import json
import telegram.error
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton, WebAppInfo, LinkPreviewOptions
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, Application, \
    ConversationHandler
from functools import partial
from re import match
from key import *
from extract_datamatrix_concurrent import *
from label_generation import generate_label_full_info, generate_label_15_20mm
from csv_handler import *
from db_adapter import *
import time
import os
from enum import StrEnum

logging.basicConfig(filename='logs.txt', filemode='a',
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.Formatter.converter = time.gmtime
logger = logging.getLogger(__name__)

FIRST, SECOND, THIRD, FOURTH, FIFTH, SIXTH, SEVENTH, EIGTH = range(8)


class ModeButtons(StrEnum):
    EPS2PDF = "EPS -> PDF",
    EPS2CSV = "EPS -> CSV",
    CSV2PDF = "CSV -> PDF",
    JSON = "JSON",
    FULL_FORMATTING = "Полноформатный",
    MM20 = "20мм/стр",
    MM15 = "15мм/стр",
    MM20_NUM = "20мм/стр  с нумерацией",
    MM15_NUM = "15мм/стр  с нумерацией",
    MM20_A4 = '20мм замостить',
    MM15_A4 = '15мм замостить',
    ZIP = 'ZIP',
    CSV = 'CSV',
    CSV_SHORT = 'CSV#2',
    XLSX = 'XLSX',
    EPS2XLSX = 'EPS -> XLSX',
    CSV2XLSX = 'CSV -> XLSX',


async def start_conversation_handler_lv0(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f'[start_conv_handler]  --  user: {update.effective_user.id}, {update.effective_user.full_name}')
    context.user_data.clear()
    reply_keyboard = [[ModeButtons.EPS2CSV, ModeButtons.CSV2PDF, ],
                      [ModeButtons.EPS2PDF, ModeButtons.JSON, ],
                      [ModeButtons.EPS2XLSX, ModeButtons.CSV2XLSX, ], ]
    await update.message.reply_text(
        'Выберите:',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True,
            resize_keyboard=True,
        ),
    )
    return FIRST


# async def convert_eps2csv_lv1(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     logger.info(f'convert_eps2csv, user: {update.effective_user.id}, {update.effective_user.full_name}')
#     reply_keyboard = [['Загрузить zip']]
#     await update.message.reply_text(
#         'Выберите:',
#         reply_markup=ReplyKeyboardMarkup(
#             reply_keyboard, one_time_keyboard=True,
#         ),
#     )
#     return SECOND


async def convert_csv2pdf_lv1(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f'[convert_csv2pdf]  --  user: {update.effective_user.id}, {update.effective_user.full_name}')
    context.user_data["upload_zip_mode"] = 'eps2csv'
    reply_keyboard = [[ModeButtons.FULL_FORMATTING], [ModeButtons.MM15, ModeButtons.MM20],
                      [ModeButtons.MM15_NUM, ModeButtons.MM20_NUM],
                      [ModeButtons.MM15_A4, ModeButtons.MM20_A4]]
    await update.message.reply_text(
        'Выберите:',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True,
            resize_keyboard=True,
        ),
    )
    return THIRD


async def convert_csv2pdf_full_info_handler_lv2(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f'[convert_csv2pdf_full_info_handler_lv2]  --  user: {update.effective_user.id}, '
                f'{update.effective_user.full_name}')
    txt_file_path = context.user_data['full_info_txt_filepath']
    user_input = update.message.text.strip('\'\"')
    if len(context.user_data['unique_GTINs']) > 0:
        GTIN = context.user_data['unique_GTINs'].pop(0)
        pattern = r'^([^,]{1,20}),([^,]{1,20}),([^,]{1,20}),([^,]{1,20}),([^,]{1,20}),([^,]{1,20}),([^,]{1,20}),' \
                  r'([^,]{1,20}),([^,]{1,20})$'
        if match(pattern, user_input):
            with open(txt_file_path, 'a') as f:
                f.write(f'{GTIN},{user_input}\n')
        else:
            await update.message.reply_text('Некорректный ввод. Должно быть предоставлено 9 значений через запятую, '
                                            'содержащих не более 20 знаков каждое. Укажите данные для GTIN '
                                            f'*{GTIN}*', parse_mode='Markdown',
                                            reply_markup=ReplyKeyboardMarkup(
                                                [['Отмена', ]], one_time_keyboard=True, resize_keyboard=True,
                                                input_field_placeholder=
                                                'название,размер,вид изделия,целевой пол,состав, '
                                                'цвет,модель,страна,ТР ТС'))
            context.user_data['unique_GTINs'].append(GTIN)
            context.user_data['unique_GTINs'] = sorted(context.user_data['unique_GTINs'])
            return FOURTH
        if len(context.user_data['unique_GTINs']) > 0:
            await update.message.reply_text(f'Принято. Укажите данные для GTIN '
                                            f'*{context.user_data["unique_GTINs"][0]}*',
                                            reply_markup=ReplyKeyboardMarkup(
                                                [['Отмена', ]], one_time_keyboard=True, resize_keyboard=True,
                                                input_field_placeholder=
                                                'название,размер,вид изделия,целевой пол,состав, '
                                                'цвет,модель,страна,ТР ТС'), parse_mode='Markdown')

        else:
            await update.message.reply_text(f'Получена информация для каждого GTIN. Начинается обработка.',
                                            reply_markup=ReplyKeyboardRemove())
            await convert_csv2pdf_full_info_done_input_lv2(update, context)
            return ConversationHandler.END


async def convert_csv2pdf_full_info_done_input_lv2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f'[convert_csv2pdf_full_info_done_input_lv2]  --  user: {update.effective_user.id}, '
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


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f'[cancel]  --  user: {update.effective_user.id}, {update.effective_user.full_name}')
    context.user_data.clear()
    await update.message.reply_text(
        "Процесс прерван.", reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


async def start_help_conversation_lv0(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f'[help_message]  --  user: {update.effective_user.id}, {update.effective_user.full_name}')
    context.user_data.clear()
    reply_keyboard = [[ModeButtons.EPS2CSV, ModeButtons.CSV2PDF],
                      [ModeButtons.JSON]]
    await update.message.reply_text(
        '''
*Доступные команды:*

/convert \- Начать процесс конвертации файлов
/cancel \- Отменить текущую операцию
/help \- Просмотреть это справочное сообщение

*Начало работы:*

1\. Отправьте команду /convert
2\. Выберите вариант конвертации \(EPS в CSV или CSV в PDF\)
3\. Загрузите требуемый файл \(ZIP или CSV\)
4\. Получите конвертированный файл

*Демо\-видео*: [EPS \-\> CSV](https://t\.me/eps_csv_pdf/23?single), [CSV \-\> PDF](https://t\.me/eps_csv_pdf/24?single)

**>1\. *EPS в CSV*
>\- Отправьте ZIP\-архив с EPS\-файлами
>\- Получите CSV\-файл, где каждая строка содержит полный код маркировки, готовый для форматирования в PDF или использования в ПО вашего принтера\.
>
>2\. *CSV в PDF*
>\- Отправьте CSV\-файл со списком кодов
>\- Выберите "Полноформатный" для формирования PDF с подробной информацией или "15мм/20мм" для PDF только с дата матрикс кодом
>\- Получите PDF, где каждый код представлен как дата матрикс на отдельной странице \(с вашими дополнительными данными при выборе полноформатного режима, только с дата матриксом на этикетках со стороной 15 или 20 миллиметров в случае выбора режима 15/20 мм\)
>
>*Образцы всех файлов, как ожидаемых от пользователя, так и получаемых в результате обработки, доступны в 
>соответствующем разделе со справочной информацией\.*
>
>Используйте меню для навигации и /help для просмотра этого сообщения еще раз\.||
        ''',
        parse_mode='MarkdownV2', link_preview_options=LinkPreviewOptions(url='https://t.me/eps_csv_pdf/28?single',
                                                                         show_above_text=False, ),
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True, ),
    )
    return FIRST


async def help_eps2csv_lv1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f'[help_eps2csv]  --  user: {update.effective_user.id}, {update.effective_user.full_name}')
    reply_keyboard = [[f'{ModeButtons.ZIP}', f'{ModeButtons.CSV}']]
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text='Здесь можно получить примеры файлов: 1) zip-архив с eps-файлами внутри, '
                                        'такой архив предоставляется Вами для обработки. 2) csv-файл со списком кодов, '
                                        'каждый код - результат преобразования eps-файла из zip-архива.',
                                   reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True,
                                                                    resize_keyboard=True))
    return SECOND


async def help_csv2pdf_lv1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f'[help_csv2pdf]  --  user: {update.effective_user.id}, {update.effective_user.full_name}')
    reply_keyboard = [[f"{ModeButtons.FULL_FORMATTING}"], [f"{ModeButtons.CSV}", f"{ModeButtons.CSV_SHORT}"],
                      [f"{ModeButtons.MM15}", f"{ModeButtons.MM20}", ],
                      [f"{ModeButtons.MM15_A4}", f"{ModeButtons.MM20_NUM}"]]
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


async def help_xlsx2json_lv1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f'[help_xlsx2json_lv1]  --  user: {update.effective_user.id}, {update.effective_user.full_name}')
    reply_keyboard = [[f"{ModeButtons.XLSX}", f"{ModeButtons.JSON}", ]]
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text='Здесь можно получить примеры файлов: 1) xlsx, 2) json',
                                   reply_markup=ReplyKeyboardMarkup(
                                       reply_keyboard, one_time_keyboard=True, resize_keyboard=True
                                   ))
    return FOURTH


async def help_download_sample_lv2(update: Update, context: ContextTypes.DEFAULT_TYPE, path):
    logger.info(f'[help_download_sample]  --  user: {update.effective_user.id}, {update.effective_user.full_name}')
    with open(path, "rb") as pdf_file:
        await context.bot.send_document(chat_id=update.effective_chat.id, reply_markup=ReplyKeyboardRemove(),
                                        document=pdf_file)

    return ConversationHandler.END


async def upload_csv(update: Update, context: ContextTypes.DEFAULT_TYPE, size, index_on, paving):
    logger.info(f'[upload_csv]  --  user: {update.effective_user.id}, {update.effective_user.full_name}')
    context.user_data["waiting_for_csv"] = True
    context.user_data['size'] = size
    context.user_data['index_on'] = index_on
    context.user_data['paving'] = paving
    if context.user_data["upload_zip_mode"] == 'eps2csv':
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Отправьте csv-файл.",
                                       reply_markup=ReplyKeyboardRemove())
    elif context.user_data["upload_zip_mode"] == 'eps2pdf':
        return await csv_file_handler(update, context)


async def check_csv_file(update, context, file, user_csv_filepath):
    await file.download_to_drive(user_csv_filepath)
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=f"CSV файл получен.", )

    row_count, incorrect_codes_count = csv_file_row_count(user_csv_filepath), \
        incorrect_csv_file_codes_count(user_csv_filepath)
    if row_count == incorrect_codes_count:
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=f"Нет корректных данных.")
        return ConversationHandler.END

    if row_count > incorrect_codes_count > 0:
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=f"Ваш csv-файл содержит некорректные коды. "
                                            f"Генерация для таких данных не происходит.")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id,
                                       action=telegram.constants.ChatAction.TYPING)


async def csv_file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # TODO: refactor this trash pile
    logger.info(f'[csv_file_handler]  --  user: {update.effective_user.id}, {update.effective_user.full_name}')
    result_pdf_filepath = f'data/user_{update.effective_user.id}/result_pdf_{uuid.uuid4()}.pdf'
    if context.user_data["upload_zip_mode"] == 'eps2pdf':
        user_csv_filepath = (
            context.user_data)['user_csv_filepath'] = context.user_data['upload_zip_eps2pdf_mode_csv_filepath']
        if context.user_data['size'] == 100:
            await csv_file_full_info_handler(update, context, user_csv_filepath)
            return FOURTH
        else:
            logger.info(f'[csv_file_handler]  --  user: {update.effective_chat.id} '
                        f"{update.effective_user.full_name}")
            generate_label_15_20mm(user_csv_filepath, int(context.user_data['size']),
                                   result_pdf_filepath, context.user_data['index_on'],
                                   context.user_data['paving'])
        with open(result_pdf_filepath, "rb") as pdf_file:
            await context.bot.send_document(chat_id=update.effective_chat.id,
                                            document=pdf_file, caption="pdf-файл доступен для загрузки.")
        delete_files([result_pdf_filepath, ])
        context.user_data["waiting_for_csv"] = False

    else:
        user_csv_filepath = Path(f'data/user_{update.effective_user.id}/csv_{uuid.uuid4()}.csv')
        user_csv_filepath.parent.mkdir(parents=True, exist_ok=True)
        context.user_data['user_csv_filepath'] = user_csv_filepath
        if context.user_data.get("waiting_for_csv", False) and context.user_data['size'] is not None:
            file = await update.message.document.get_file()
            await context.bot.send_chat_action(chat_id=update.effective_chat.id,
                                               action=telegram.constants.ChatAction.TYPING)
            if file.file_path.endswith('.csv'):
                if one_time_result := await check_csv_file(update, context, file, user_csv_filepath) is not None:
                    return one_time_result
                if context.user_data['size'] == 100:
                    await csv_file_full_info_handler(update, context, user_csv_filepath)
                    return FOURTH
                else:
                    logger.info(f'[csv_file_handler]  --  user: {update.effective_chat.id} '
                                f"user_data: {context.user_data}")
                    generate_label_15_20mm(user_csv_filepath, int(context.user_data['size']),
                                           result_pdf_filepath, context.user_data['index_on'],
                                           context.user_data['paving'])
                with open(result_pdf_filepath, "rb") as pdf_file:
                    await context.bot.send_document(chat_id=update.effective_chat.id,
                                                    document=pdf_file, caption="pdf-файл доступен для загрузки.")
                delete_files([result_pdf_filepath, ])
                context.user_data["waiting_for_csv"] = False
            else:
                await context.bot.send_message(chat_id=update.effective_chat.id, text="Отправляйте только csv-файлы.")
        logger.info(f'[csv_file_handler] finishes  --  user: {update.effective_user.id}, {update.effective_user.full_name}')
    return ConversationHandler.END


async def csv_file_full_info_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, user_csv_filepath):
    logger.info(f'[csv_file_handler]  --  user: {update.effective_chat}')
    context.user_data['full_info_txt_filepath'] = f'data/user_{update.effective_user.id}/' \
                                                  f'full_info_txt_{uuid.uuid4()}.txt'

    context.user_data['unique_GTINs'] = gtin_set(user_csv_filepath)
    await context.bot.send_message(chat_id=update.effective_chat.id, parse_mode='Markdown',
                                   reply_markup=ReplyKeyboardMarkup(
                                       [['Отмена', ]], one_time_keyboard=True, resize_keyboard=True,
                                       input_field_placeholder=
                                       'название,размер,вид изделия,целевой пол,состав, '
                                       'цвет,модель,страна,ТР ТС'),
                                   text=f'Ваши уникальные GTIN\'ы: '
                                        f'{context.user_data["unique_GTINs"]}. '
                                        f'Данные вводятся через запятую для каждого запрошенного GTIN. '
                                        f'Например: '
                                        f'"название,размер,вид изделия,целевой пол,состав,'
                                        f'цвет,модель,страна,ТР ТС". Укажите данные для GTIN '
                                        f'*{context.user_data["unique_GTINs"][0]}*', )
    context.user_data["waiting_for_csv"] = False
    logger.info(
        f'[csv_file_handler] finishes  --  user: {update.effective_user.id}, {update.effective_user.full_name}')


async def upload_zip(update: Update, context: ContextTypes.DEFAULT_TYPE, mode):
    logger.info(f'[upload_zip]  --  user: {update.effective_user.id}, {update.effective_user.full_name}')

    # user_id = update.effective_user.id
    # result = check_rate_limit(user_id, max_calls=3, time_frame=300)
    # if not result["allowed"]:
    #     await update.message.reply_text(f"Количество запросов ограничено. Доступ возобновится через "
    #                                     f"{result['remaining_time']} секунд(ы).")
    #     return ConversationHandler.END

    await context.bot.send_message(chat_id=update.effective_chat.id, text="Отправьте zip-файл. Размер не более 20 Мб.",
                                   reply_markup=ReplyKeyboardRemove())
    context.user_data["upload_zip_mode"] = mode
    context.user_data["waiting_for_zip"] = True
    return SECOND


async def zip_file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f'[zip_file_handler]  --  user: {update.effective_user.id}, {update.effective_user.full_name}')
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
            # await context.bot.send_message(chat_id=update.effective_chat.id,
            #                                text=f'Времени затрачено на конвертацию: {time.time() - start:.1f} сек.')
            logger.info(f'[zip_file_handler], eps2csv took {time.time() - start:.1f} sec for user '
                        f'{update.effective_chat.id} {update.effective_user.full_name}')
            if context.user_data["upload_zip_mode"] == 'eps2csv':
                if os.stat(user_csv_filepath).st_size != 0:
                    with open(user_csv_filepath, "rb") as csv_file:
                        # TODO: what if zip file was empty or contained incorrect files? it must not be void
                        await context.bot.send_document(chat_id=update.effective_chat.id,
                                                        document=csv_file, caption="csv-файл готов для загрузки.")
                    # delete_files([user_zip_filepath, ])
                else:
                    await context.bot.send_message(chat_id=update.effective_chat.id,
                                                   text=f'Ошибка. Проверьте исходные данные.')
            else:
                context.user_data["upload_zip_eps2pdf_mode_csv_filepath"] = user_csv_filepath
                reply_keyboard = [[ModeButtons.FULL_FORMATTING], [ModeButtons.MM15, ModeButtons.MM20],
                                  [ModeButtons.MM15_NUM, ModeButtons.MM20_NUM],
                                  [ModeButtons.MM15_A4, ModeButtons.MM20_A4]]
                await update.message.reply_text(
                    'Выберите:',
                    reply_markup=ReplyKeyboardMarkup(
                        reply_keyboard, one_time_keyboard=True,
                        resize_keyboard=True,
                    ),
                )
                return THIRD
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Отправляйте только zip-файлы.")

    logger.info(f'[zip_file_handler] finishes  --  user: {update.effective_user.id}, {update.effective_user.full_name}')
    return ConversationHandler.END


async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # TODO: null value for unfilled optional parametres
    logger.info(f'[web_app_data]  --  user: {update.effective_user.id}, {update.effective_user.full_name}')
    user_json_filepath = Path(f'data/user_{update.effective_user.id}/json_{uuid.uuid4()}.json')
    user_json_filepath.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(update.effective_message.web_app_data.data)
    data['products'] = context.user_data['xlsx_data'][0]
    if context.user_data['xlsx_data'][1] == 'errors':
        await update.message.reply_html(text=f"Данные содержат ошибки", reply_markup=ReplyKeyboardRemove(), )
    else:
        await update.message.reply_html(text=f"Данные получены", reply_markup=ReplyKeyboardRemove(), )
    data_trimmed = {k: v for k, v in data.items() if v}
    for key, value in data_trimmed.items():
        if value == 'null':
            data_trimmed[key] = None
    with open(user_json_filepath, "w") as json_file:
        json.dump(data_trimmed, json_file)
    with open(user_json_filepath, "rb") as json_file:
        await context.bot.send_document(chat_id=update.effective_chat.id,
                                        document=json_file, caption="json доступен для загрузки.")
    return ConversationHandler.END


async def json_handler_upload_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f'[json_handler_upload_file]  --  user: {update.effective_user.id}, {update.effective_user.full_name}')
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Отправьте файл.",
                                   reply_markup=ReplyKeyboardRemove())
    context.user_data["waiting_for_xlsx"] = True
    return FIFTH


async def json_handler_file_processing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f'[json_handler_file_processing]  --  user: {update.effective_user.id}, '
                f'{update.effective_user.full_name}')
    user_xlsx_filepath = Path(f'data/user_{update.effective_user.id}/xlsx_{uuid.uuid4()}.xlsx')
    user_xlsx_filepath.parent.mkdir(parents=True, exist_ok=True)

    if context.user_data.get("waiting_for_xlsx", False):
        try:
            file = await update.message.document.get_file()
            await context.bot.send_chat_action(chat_id=update.effective_chat.id,
                                               action=telegram.constants.ChatAction.TYPING)
        except telegram.error.BadRequest:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Ошибка.")
            return ConversationHandler.END

        if file.file_path.endswith('.xlsx'):
            await file.download_to_drive(user_xlsx_filepath)
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"XLSX получен.")
            context.user_data['xlsx_data'] = xlsx_file_exctract_data(user_xlsx_filepath)
            # delete_files([user_xlsx_filepath, ])
            await update.message.reply_text(
                "Выберите:",
                reply_markup=ReplyKeyboardMarkup.from_button(KeyboardButton(text="Вывод из оборота", web_app=WebAppInfo
                (url=f"https://vps658a992f8c340385650937.noezserver.de/js/withdraw"), )), )
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Отправляйте только xlsx-файлы.")
    return SIXTH


async def csv2xlsx_upload_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f'[csv2xlsx_upload_file]  --  user: {update.effective_user.id}, {update.effective_user.full_name}')
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Отправьте файл.",
                                   reply_markup=ReplyKeyboardRemove())
    context.user_data["waiting_for_file"] = True
    return EIGTH


async def convert_csv2xlsx(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f'[json_handler_file_processing]  --  user: {update.effective_user.id}, '
                f'{update.effective_user.full_name}')
    user_xlsx_filepath = Path(f'data/user_{update.effective_user.id}/xlsx_{uuid.uuid4()}.xlsx')
    user_xlsx_filepath.parent.mkdir(parents=True, exist_ok=True)
    user_csv_filepath = Path(f'data/user_{update.effective_user.id}/csv_{uuid.uuid4()}.csv')
    user_zip_filepath = Path(f'data/user_{update.effective_user.id}/zip_{uuid.uuid4()}.zip')
    handle_zip_working_directory_path = Path(f'data/user_{update.effective_user.id}/data_{uuid.uuid4()}')

    if context.user_data.get("waiting_for_file", False):
        try:
            file = await update.message.document.get_file()
            await context.bot.send_chat_action(chat_id=update.effective_chat.id,
                                               action=telegram.constants.ChatAction.TYPING)
        except telegram.error.BadRequest:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Ошибка.")
            return ConversationHandler.END

        if file.file_path.endswith('.csv'):
            await file.download_to_drive(user_csv_filepath)
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"CSV получен.")
            csv2xlsx_convert(user_csv_filepath, user_xlsx_filepath)
            with open(user_xlsx_filepath, "rb") as xlsx_file:
                await context.bot.send_document(chat_id=update.effective_chat.id,
                                                document=xlsx_file, caption="xlsx-файл готов для загрузки.")
        elif file.file_path.endswith('.zip'):
            await file.download_to_drive(user_zip_filepath)
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"ZIP получен.")
            await handle_zip(zip_filepath=user_zip_filepath, csv_filepath=user_csv_filepath,
                             work_directory_path=handle_zip_working_directory_path)
            csv2xlsx_convert(user_csv_filepath, user_xlsx_filepath)
            with open(user_xlsx_filepath, "rb") as xlsx_file:
                await context.bot.send_document(chat_id=update.effective_chat.id,
                                                document=xlsx_file, caption="xlsx-файл готов для загрузки.")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Отправляйте только csv или "
                                                                           "zip-файлы.")
    return ConversationHandler.END


async def post_init(application: Application) -> None:
    await application.bot.set_my_commands([('convert', 'Начать преобразование'), ['cancel', 'Прервать диалог'],
                                           ('help', 'Показать справку')])


if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).post_init(post_init).concurrent_updates(False).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("convert", start_conversation_handler_lv0)],
        states={
            FIRST: [MessageHandler(filters.Regex(f"^{ModeButtons.EPS2CSV}$"), partial(upload_zip, mode='eps2csv')),
                    MessageHandler(filters.Regex(f"^{ModeButtons.EPS2PDF}$"), partial(upload_zip, mode='eps2pdf')),
                    MessageHandler(filters.Regex(f"^{ModeButtons.EPS2XLSX}$"), csv2xlsx_upload_file),
                    MessageHandler(filters.Regex(f"^{ModeButtons.CSV2PDF}$"), convert_csv2pdf_lv1),
                    MessageHandler(filters.Regex(f"^{ModeButtons.CSV2XLSX}$"), csv2xlsx_upload_file),
                    MessageHandler(filters.Regex(f"^{ModeButtons.JSON}$"), json_handler_upload_file),
                    MessageHandler(filters.Regex(f"^(?!{ModeButtons.EPS2CSV}$|{ModeButtons.CSV2PDF}$|"
                                                 f"{ModeButtons.JSON}$|{ModeButtons.EPS2PDF}$|"
                                                 f"{ModeButtons.EPS2XLSX}$|{ModeButtons.CSV2XLSX}$).*$"), cancel), ],
            SECOND: [  # MessageHandler(filters.Regex('Загрузить zip'), upload_zip),
                MessageHandler(filters.Regex("^(?!Загрузить zip$).*$"), cancel),
                MessageHandler(filters.Document.ZIP, zip_file_handler)],
            THIRD: [MessageHandler(filters.Regex(f"^{ModeButtons.FULL_FORMATTING}$"),
                                   partial(upload_csv, size=100, index_on=False, paving=False)),
                    MessageHandler(filters.Regex(f"^{ModeButtons.MM15}$"),
                                   partial(upload_csv, size=15, index_on=False, paving=False)),
                    MessageHandler(filters.Regex(f"^{ModeButtons.MM20}$"),
                                   partial(upload_csv, size=20, index_on=False, paving=False)),
                    MessageHandler(filters.Regex(f"^{ModeButtons.MM15_NUM}$"),
                                   partial(upload_csv, size=15, index_on=True, paving=False)),
                    MessageHandler(filters.Regex(f"^{ModeButtons.MM20_NUM}$"),
                                   partial(upload_csv, size=20, index_on=True, paving=False)),
                    MessageHandler(filters.Regex(f"^{ModeButtons.MM15_A4}$"),
                                   partial(upload_csv, size=15, index_on=False, paving=True)),
                    MessageHandler(filters.Regex(f"^{ModeButtons.MM20_A4}$"),
                                   partial(upload_csv, size=20, index_on=False, paving=True)),
                    MessageHandler(filters.Regex(
                        f"^(?!{ModeButtons.FULL_FORMATTING}$|{ModeButtons.MM15}$|{ModeButtons.MM20}$|"
                        f"{ModeButtons.MM15_NUM}$|{ModeButtons.MM20_NUM}$|"
                        f"{ModeButtons.MM15_A4}$|{ModeButtons.MM20_A4}$).*$"), cancel),
                    MessageHandler(filters.Document.FileExtension("csv"), csv_file_handler)],
            FOURTH: [CommandHandler("cancel", cancel),
                     MessageHandler(filters.Regex("^(?!Отмена$).*$"), convert_csv2pdf_full_info_handler_lv2),
                     MessageHandler(filters.Regex('Отмена'), cancel), ],
            FIFTH: [
                MessageHandler(filters.Regex("^(?!Загрузить xlsx$).*$"), cancel),
                MessageHandler(filters.Document.FileExtension('xlsx'), json_handler_file_processing)],
            SIXTH: [
                MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data)],
            SEVENTH: [
                MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data)],
            EIGTH: [
                MessageHandler(filters.Document.FileExtension("csv"), convert_csv2xlsx),
                MessageHandler(filters.Document.ZIP, convert_csv2xlsx),
                MessageHandler(filters.Regex("^(?!Загрузить zip$).*$"), cancel),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv_handler)
    help_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('help', start_help_conversation_lv0),
                      CommandHandler('start', start_help_conversation_lv0)],
        states={
            FIRST: [MessageHandler(filters.Regex(f"^{ModeButtons.EPS2CSV}$"), help_eps2csv_lv1),
                    MessageHandler(filters.Regex(f"^{ModeButtons.CSV2PDF}$"), help_csv2pdf_lv1),
                    MessageHandler(filters.Regex(f"^{ModeButtons.JSON}$"), help_xlsx2json_lv1),
                    MessageHandler(filters.Regex(f"^(?!{ModeButtons.EPS2CSV}$|{ModeButtons.CSV2PDF}$).*$"), cancel), ],
            SECOND: [MessageHandler(filters.Regex(f'{ModeButtons.ZIP}'),
                                    partial(help_download_sample_lv2,
                                            path='data/demo_samples/sample_eps2csv_archive.zip')),
                     MessageHandler(filters.Regex(f'{ModeButtons.CSV}'),
                                    partial(help_download_sample_lv2,
                                            path='data/demo_samples/sample_eps2csv_result.csv')),
                     MessageHandler(filters.Regex(f"^(?!{ModeButtons.ZIP}$|{ModeButtons.CSV}$).*$"), cancel), ],
            THIRD: [MessageHandler(filters.Regex(f'{ModeButtons.CSV_SHORT}'),
                                   partial(help_download_sample_lv2,
                                           path='data/demo_samples/sample_csv2pdf_15_20mm.csv')),
                    MessageHandler(filters.Regex(f'{ModeButtons.CSV}'),
                                   partial(help_download_sample_lv2,
                                           path='data/demo_samples/sample_csv2pdf_full_info.csv')),
                    MessageHandler(filters.Regex(f'{ModeButtons.MM20_NUM}'),
                                   partial(help_download_sample_lv2,
                                           path='data/demo_samples/sample_csv2pdf_label_20mm_num.pdf')),
                    MessageHandler(filters.Regex(f'{ModeButtons.MM15_A4}'),
                                   partial(help_download_sample_lv2,
                                           path='data/demo_samples/sample_csv2pdf_label_15mm_a4.pdf')),
                    MessageHandler(filters.Regex(f'{ModeButtons.MM20}'),
                                   partial(help_download_sample_lv2,
                                           path='data/demo_samples/sample_csv2pdf_label_20mm.pdf')),
                    MessageHandler(filters.Regex(f'{ModeButtons.MM15}', ),
                                   partial(help_download_sample_lv2,
                                           path='data/demo_samples/sample_csv2pdf_label_15mm.pdf')),
                    MessageHandler(filters.Regex(f'{ModeButtons.FULL_FORMATTING}'),
                                   partial(help_download_sample_lv2,
                                           path='data/demo_samples/sample_csv2pdf_label_full_info.pdf')),
                    MessageHandler(filters.Regex(f"^(?!{ModeButtons.ZIP}$|{ModeButtons.CSV}$|"
                                                 f"{ModeButtons.MM20}$|{ModeButtons.MM15}$|"
                                                 f"{ModeButtons.FULL_FORMATTING}|{ModeButtons.CSV_SHORT}$|"
                                                 f"{ModeButtons.MM20_NUM}$|{ModeButtons.MM15_A4}$).*$"), cancel),
                    ],
            FOURTH: [
                 MessageHandler(filters.Regex(f'{ModeButtons.XLSX}'),
                                partial(help_download_sample_lv2,
                                        path='data/demo_samples/sample_xlsx2json.xlsx')),
                 MessageHandler(filters.Regex(f'{ModeButtons.JSON}'),
                                partial(help_download_sample_lv2,
                                        path='data/demo_samples/sample_xlsx2json.json')),
                 MessageHandler(filters.Regex(f"^(?!{ModeButtons.XLSX}$|{ModeButtons.JSON}$).*$"), cancel),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    # app.add_handler(CommandHandler('start', start_help_conversation_lv0))
    app.add_handler(help_conv_handler)
    app.run_polling(allowed_updates=Update.ALL_TYPES)
