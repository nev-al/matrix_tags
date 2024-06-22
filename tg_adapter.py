import telegram.error
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, Application, \
    ConversationHandler
from functools import partial
from re import match
from key import *
from extract_datamatrix_concurrent import *
from label import generate_label_full_info, generate_label_15_20mm
from csv_handler import *
import time

logging.basicConfig(filename='logs.txt', filemode='a',
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.Formatter.converter = time.gmtime
logger = logging.getLogger(__name__)

FIRST, SECOND, THIRD, FOURTH = range(4)


async def start_conversation_handler_lv0(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f'start_conv_handler, user {update.effective_chat.id} {update.effective_user.full_name}')
    reply_keyboard = [['EPS -> CSV', 'CSV -> PDF']]
    await update.message.reply_text(
        'Выберите:',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True,
            resize_keyboard=True,
        ),
    )
    return FIRST


# async def convert_eps2csv_lv1(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     logger.info(f'convert_eps2csv, user {update.effective_chat.id} {update.effective_user.full_name}')
#     reply_keyboard = [['Загрузить zip']]
#     await update.message.reply_text(
#         'Выберите:',
#         reply_markup=ReplyKeyboardMarkup(
#             reply_keyboard, one_time_keyboard=True,
#         ),
#     )
#     return SECOND


async def convert_csv2pdf_lv1(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f'convert_csv2pdf, user {update.effective_chat.id} {update.effective_user.full_name}')
    reply_keyboard = [['Полноформатный', 'Датаматрикс 15 мм', 'Датаматрикс 20 мм']]
    await update.message.reply_text(
        'Выберите:',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True,
            resize_keyboard=True,
        ),
    )
    return THIRD


async def convert_csv2pdf_full_info_handler_lv2(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f'convert_csv2pdf_full_info_handler_lv2, user {update.effective_chat.id} '
                f'{update.effective_user.full_name}')
    txt_file_path = context.user_data['full_info_txt_filepath']
    user_input = update.message.text.strip('\'\"')
    pattern = r'^(\d{14}),([^,]{1,20}),([^,]{1,20}),([^,]{1,20}),([^,]{1,20}),([^,]{1,20}),([^,]{1,20}),([^,]{1,20}),' \
              r'([^,]{1,20}),([^,]{1,20})$'
    if match(pattern, user_input):
        with open(txt_file_path, 'a') as f:
            f.write(f'{user_input}\n')
        await update.message.reply_text('Принято. Добавите что-то ещё? Нажмите "Готово" для завершения ввода. ',
                                        reply_markup=ReplyKeyboardMarkup([['Готово', ]], one_time_keyboard=True,
                                                                         resize_keyboard=True, ))
    else:
        await update.effective_user.send_message('Некорректный ввод. Ограничения: GTIN (в первой позиции) 14 цифр, '
                                                 'остальные значения не более 20 знаков.')

    return FOURTH


async def convert_csv2pdf_full_info_done_input_lv2(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f'convert_csv2pdf_full_info_done_input_lv2, user {update.effective_chat.id} '
                f'{update.effective_user.full_name}')
    full_info_txt_filepath = context.user_data['full_info_txt_filepath']
    full_info_user_csv_filepath = context.user_data['user_csv_filepath']
    full_info_joined_csv_filepath = Path(f'data/user_{update.effective_user.id}/'
                                         f'full_info_joined_csv_{uuid.uuid4()}.csv')
    full_info_result_pdf_filepath = f'data/user_{update.effective_user.id}/full_info_pdf_{uuid.uuid4()}.pdf'
    join_strings(full_info_user_csv_filepath, full_info_txt_filepath, full_info_joined_csv_filepath)
    generate_label_full_info(full_info_joined_csv_filepath, full_info_result_pdf_filepath)

    with open(full_info_result_pdf_filepath, "rb") as pdf_file:
        await context.bot.send_document(chat_id=update.effective_chat.id, reply_markup=ReplyKeyboardRemove(),
                                        document=pdf_file, caption="PDF доступен для загрузки.")

    delete_files([full_info_txt_filepath, full_info_user_csv_filepath, full_info_result_pdf_filepath], )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f'cancel, user {update.effective_chat.id} {update.effective_user.full_name}')
    await update.message.reply_text(
        "Процесс прерван.", reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


async def start_help_conversation_lv0(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f'help_message, user {update.effective_chat.id} {update.effective_user.full_name}')
    # await update.effective_user.send_video('data/demo_samples/img.gif')
    reply_keyboard = [['EPS -> CSV', 'CSV -> PDF']]
    await update.message.reply_text(
        '''
*Доступные команды:*

/convert - Начать процесс конвертации файлов
/cancel - Отменить текущую операцию
/help - Просмотреть это справочное сообщение

*Варианты конвертации:*

1. *EPS в CSV*
- Отправьте ZIP-архив с EPS-файлами
- Получите CSV-файл, где каждая строка содержит декодированные данные матрицы данных

2. *CSV в PDF*
- Отправьте CSV-файл со списком кодов
- Выберите "`Полноформатный`" для формирования PDF с подробной информацией или "`15мм`/`20мм`" для PDF только с матрицами данных
- Получите PDF, где каждый код представлен как матрица данных на отдельной странице (с вашими дополнительными данными при выборе полноформатного режима, только матрицы данных на листах со стороной 15 или 20 миллиметров в случае выбора режима 15/20 мм)

*Начало работы:*

1. Отправьте команду /convert
2. Выберите вариант конвертации (EPS в CSV или CSV в PDF)
3. Загрузите требуемый файл (`ZIP` или `CSV`)
- - Для конвертации CSV в PDF выберите формат вывода (`Полноформатный` или `15мм`/`20мм`)
4. Получите конвертированный файл

*Образцы всех файлов, как ожидаемых от пользователя, так и получаемых в результате обработки, можно загрузить в 
соответствующем разделе со справочной информацией.*

Используйте меню для навигации и /help для просмотра этого сообщения еще раз.
        ''',
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True,
            resize_keyboard=True,
        ),
    )
    return FIRST


# async def coming_soon(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     print(context.user_data)
#     logger.info(f'func coming_soon, user {update.effective_chat.id} {update.effective_user.full_name}')
#     await context.bot.send_message(chat_id=update.effective_chat.id,
#                                    text='Coming soon.', reply_markup=ReplyKeyboardRemove())
#     return ConversationHandler.END


async def help_eps2csv_lv1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f'help_eps2csv, user {update.effective_chat.id} {update.effective_user.full_name}')
    reply_keyboard = [['Ваш zip', 'Итоговый csv']]
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text='Здесь можно получить примеры файлов: 1) zip-архив с eps-файлами внутри, '
                                        'такой архив предоставляется Вами для обработки. 2) csv-файл со списком кодов, '
                                        'каждый код - результат преобразования eps-файла из zip-архива.',
                                   reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True,
                                                                    resize_keyboard=True))
    return SECOND


async def help_csv2pdf_lv1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f'help_csv2pdf, user {update.effective_chat.id} {update.effective_user.full_name}')
    reply_keyboard = [['Ваш csv для получения полноформатного pdf', 'Ваш csv для получения 15мм или 20мм',
                       'Итоговый pdf с кодами 20мм', 'Итоговый pdf с кодами 15мм',
                       'Итоговый полноформатный pdf']]
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text='Здесь можно получить примеры файлов: 1) csv-файл с кодами для преобразования '
                                        'в pdf-файл с полной информацией 2) csv-файл с кодами для получения 15 или '
                                        '20 миллиметровых датаматриксов 3) pdf-файл c 15 миллиметровыми датаматриксами '
                                        '4) pdf-файл c 20 миллиметровыми датаматриксами 5) pdf-файл c датаматриксами и '
                                        'полной информацией о них',
                                   reply_markup=ReplyKeyboardMarkup(
                                       reply_keyboard, one_time_keyboard=True, resize_keyboard=True
                                   ))
    return THIRD


async def help_download_sample_lv2(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    logger.info(f'func help_download_sample, user {update.effective_chat.id} {update.effective_user.full_name}')
    with open(path, "rb") as pdf_file:
        await context.bot.send_document(chat_id=update.effective_chat.id, reply_markup=ReplyKeyboardRemove(),
                                        document=pdf_file)

    return ConversationHandler.END


async def upload_csv(update: Update, context: ContextTypes.DEFAULT_TYPE, size):
    logger.info(f'upload_csv, user {update.effective_chat.id} {update.effective_user.full_name}')
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Отправьте csv-файл.",
                                   reply_markup=ReplyKeyboardRemove())
    context.user_data["waiting_for_csv"] = True
    context.user_data['size'] = size


async def csv_file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f'csv_file_handler, user {update.effective_chat.id} {update.effective_user.full_name}')
    user_csv_filepath = Path(f'data/user_{update.effective_user.id}/csv_{uuid.uuid4()}.csv')
    user_csv_filepath.parent.mkdir(parents=True, exist_ok=True)
    context.user_data['user_csv_filepath'] = user_csv_filepath
    result_pdf_filepath = f'data/user_{update.effective_user.id}/result_pdf_{uuid.uuid4()}.pdf'
    if context.user_data.get("waiting_for_csv", False) and context.user_data['size'] is not None:
        file = await update.message.document.get_file()
        await context.bot.send_chat_action(chat_id=update.effective_chat.id,
                                           action=telegram.constants.ChatAction.TYPING)
        if file.file_path.endswith('.csv'):
            await file.download_to_drive(user_csv_filepath)
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text=f"CSV файл получен.", )
            await context.bot.send_chat_action(chat_id=update.effective_chat.id,
                                               action=telegram.constants.ChatAction.TYPING)

            if context.user_data['size'] == 100:
                logger.info(f'csv_file_handler - full info mode, user {update.effective_chat.id} '
                            f'{update.effective_user.full_name}')
                txt_file_path = Path(f'data/user_{update.effective_user.id}/full_info_txt_{uuid.uuid4()}.txt')
                context.user_data['full_info_txt_filepath'] = txt_file_path
                wrong_codes = get_wrong_codes(user_csv_filepath)
                if len(wrong_codes) > 0:
                    await context.bot.send_message(chat_id=update.effective_chat.id,
                                                   text=f"Ваш csv-файл содержит некорректные коды: {wrong_codes}. "
                                                        f"Генерация для указанных данных не происходит.")
                data_grouped_by_unique_gtin = group_by_gtin(user_csv_filepath)
                await context.bot.send_message(chat_id=update.effective_chat.id,
                                               text=f'Ваши уникальные GTIN\'ы: '
                                                    f'{tuple(data_grouped_by_unique_gtin.keys())}. '
                                                    f'Введите данные для каждого GTIN. Данные принимаются по одной '
                                                    f'строке за раз. После каждой отправленной строки будет '
                                                    f'предложено ввести ещё строку или завершить ввод. '
                                                    f'Используйте формат '
                                                    f'"GTIN,название,цвет,размер,дата". Например: '
                                                    f'"04620236343458,название,размер,вид изделия,целевой пол,состав,'
                                                    f'цвет,модель,страна,ТР ТС"', )
                context.user_data["waiting_for_csv"] = False
                logger.info(
                    f'csv_file_handler finishes, user {update.effective_chat.id} {update.effective_user.full_name}')
                return FOURTH
            elif context.user_data['size'] == 20 or 15:
                logger.info(f'csv_file_handler - 15/20mm mode, user {update.effective_chat.id} '
                            f'{update.effective_user.full_name}')
                generate_label_15_20mm(user_csv_filepath, filename=result_pdf_filepath,
                                       label_size=int(context.user_data['size']))
            with open(result_pdf_filepath, "rb") as pdf_file:
                await context.bot.send_document(chat_id=update.effective_chat.id,
                                                document=pdf_file, caption="pdf-файл доступен для загрузки.")

            delete_files([result_pdf_filepath, ])
            context.user_data["waiting_for_csv"] = False
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Отправляйте только csv-файлы.")

    logger.info(f'csv_file_handler finishes, user {update.effective_chat.id} {update.effective_user.full_name}')
    return ConversationHandler.END


async def upload_zip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f'upload_zip, user {update.effective_chat.id} {update.effective_user.full_name}')
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Отправьте zip-файл. Размер не более 20 Мб.",
                                   reply_markup=ReplyKeyboardRemove())
    context.user_data["waiting_for_zip"] = True
    return SECOND


async def zip_file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f'zip_file_handler, user {update.effective_chat.id} {update.effective_user.full_name}')
    user_zip_filepath = Path(f'data/user_{update.effective_user.id}/zip_{uuid.uuid4()}.zip')
    user_zip_filepath.parent.mkdir(parents=True, exist_ok=True)
    user_csv_filepath = Path(f'data/user_{update.effective_user.id}/csv_{uuid.uuid4()}.csv')
    handle_zip_working_directory_path = Path(f'data/user_{update.effective_user.id}/data_{uuid.uuid4()}')
    if context.user_data.get("waiting_for_zip", False):
        try:
            file = await update.message.document.get_file()
            await context.bot.send_chat_action(chat_id=update.effective_chat.id,
                                               action=telegram.constants.ChatAction.TYPING)
        except telegram.error.BadRequest:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Слишком большой файл. Не более 20 "
                                                                                  f"Мб допускается.")
            return ConversationHandler.END

        if file.file_path.endswith('.zip'):
            await file.download_to_drive(user_zip_filepath)
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"ZIP получен. При отсутствии "
                                                                                  f"очереди, на обработку 1000 EPS "
                                                                                  f"требуется около 20 сек.")
            await context.bot.send_chat_action(chat_id=update.effective_chat.id,
                                               action=telegram.constants.ChatAction.TYPING)
            start = time.time()
            await handle_zip(zip_filepath=user_zip_filepath, csv_filepath=user_csv_filepath,
                             work_directory_path=handle_zip_working_directory_path)
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text=f'Времени затрачено на конвертацию: {time.time() - start:.1f} сек.')
            logger.info(f'zip_file_handler, eps2csv took {time.time() - start:.1f} sec for user '
                        f'{update.effective_chat.id} {update.effective_user.full_name}')
            with open(user_csv_filepath, "rb") as csv_file:
                await context.bot.send_document(chat_id=update.effective_chat.id,
                                                document=csv_file, caption="csv-файл готов для загрузки.")
            delete_files([user_zip_filepath, ])
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Отправляйте только zip-файлы.")

    logger.info(f'zip_file_handler finishes, user {update.effective_chat.id} {update.effective_user.full_name}')
    return ConversationHandler.END


async def post_init(application: Application) -> None:
    await application.bot.set_my_commands([('convert', 'Начать преобразование'), ['cancel', 'Прервать диалог'],
                                           ('help', 'Показать справку')])


if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).post_init(post_init).concurrent_updates(False).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("convert", start_conversation_handler_lv0)],
        states={
            FIRST: [MessageHandler(filters.Regex("^EPS -> CSV$"), upload_zip),
                    MessageHandler(filters.Regex("^CSV -> PDF$"), convert_csv2pdf_lv1),
                    MessageHandler(filters.Regex("^(?!EPS -> CSV$|CSV -> PDF$).*$"), cancel), ],
            SECOND: [  # MessageHandler(filters.Regex('Загрузить zip'), upload_zip),
                MessageHandler(filters.Regex("^(?!Загрузить zip$).*$"), cancel),
                MessageHandler(filters.Document.ZIP, zip_file_handler)],
            THIRD: [MessageHandler(filters.Regex("^Полноформатный$"), partial(upload_csv, size=100)),
                    MessageHandler(filters.Regex("^Датаматрикс 15 мм$"), partial(upload_csv, size=15)),
                    MessageHandler(filters.Regex("^Датаматрикс 20 мм$"), partial(upload_csv, size=20)),
                    MessageHandler(filters.Regex(
                        "^(?!Полноформатный$|Датаматрикс 15 мм$|Датаматрикс 20 мм$).*$"), cancel),
                    MessageHandler(filters.Document.FileExtension("csv"), csv_file_handler)],
            FOURTH: [CommandHandler("cancel", cancel),
                     MessageHandler(filters.Regex("^(?!Готово$).*$"), convert_csv2pdf_full_info_handler_lv2),
                     MessageHandler(filters.Regex('Готово'), convert_csv2pdf_full_info_done_input_lv2), ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv_handler)
    help_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('help', start_help_conversation_lv0)],
        states={
            FIRST: [MessageHandler(filters.Regex("^EPS -> CSV$"), help_eps2csv_lv1),
                    MessageHandler(filters.Regex("^CSV -> PDF$"), help_csv2pdf_lv1),
                    MessageHandler(filters.Regex("^(?!EPS -> CSV$|CSV -> PDF$).*$"), cancel), ],
            SECOND: [MessageHandler(filters.Regex('Ваш zip'),
                                    partial(help_download_sample_lv2,
                                            path='data/demo_samples/sample_eps2csv_archive_1000.zip')),
                     MessageHandler(filters.Regex('Итоговый csv'),
                                    partial(help_download_sample_lv2,
                                            path='data/demo_samples/sample_eps2csv_result.csv')),
                     MessageHandler(filters.Regex("^(?!Ваш zip$|Итоговый csv$).*$"), cancel), ],
            THIRD: [MessageHandler(filters.Regex('Ваш csv для получения 15мм или 20мм'),
                                   partial(help_download_sample_lv2,
                                           path='data/demo_samples/sample_csv2pdf_15_20mm.csv')),
                    MessageHandler(filters.Regex('Ваш csv для получения полноформатного pdf'),
                                   partial(help_download_sample_lv2,
                                           path='data/demo_samples/sample_csv2pdf_full_info.csv')),
                    MessageHandler(filters.Regex('Итоговый pdf с кодами 20мм'),
                                   partial(help_download_sample_lv2,
                                           path='data/demo_samples/sample_csv2pdf_label_20mm.pdf')),
                    MessageHandler(filters.Regex('Итоговый pdf с кодами 15мм', ),
                                   partial(help_download_sample_lv2,
                                           path='data/demo_samples/sample_csv2pdf_label_15mm.pdf')),
                    MessageHandler(filters.Regex('Итоговый полноформатный pdf'),
                                   partial(help_download_sample_lv2,
                                           path='data/demo_samples/sample_csv2pdf_label_full_info.pdf')),
                    MessageHandler(filters.Regex("^(?!Ваш csv для получения 15мм или 20мм$|"
                                                 "Ваш csv для получения полноформатного pdf$|"
                                                 "Итоговый pdf с кодами 20мм$|Итоговый pdf с кодами 15мм$|"
                                                 "Итоговый полноформатный pdf$).*$"), cancel),
                    ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(CommandHandler('start', start_help_conversation_lv0))
    app.add_handler(help_conv_handler)
    app.run_polling(allowed_updates=Update.ALL_TYPES)
