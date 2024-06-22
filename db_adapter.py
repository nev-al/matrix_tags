from pony.orm import Database, Required, Set, PrimaryKey
from datetime import datetime, timedelta
from functools import wraps
from telegram.ext import Updater, CommandHandler

db = Database()


class User(db.Entity):
    id = PrimaryKey(int)
    telegram_user_id = Required(str)
    last_access = Required(datetime)
    access_count = Required(int)


db.bind(provider='sqlite', filename='users.db', create_db=True)
db.generate_mapping(create_tables=True)


def rate_limit(max_calls, time_frame):
    def decorator(func):
        @wraps(func)
        def wrapper(update, context, *args, **kwargs):
            from pony.orm import db_session

            user_id = update.effective_user.id
            current_time = datetime.now()

            with db_session:
                user = User.get(id=user_id)
                if user is None:
                    # New user
                    User(id=user_id, last_access=current_time, access_count=1)
                else:
                    time_passed = current_time - user.last_access
                    if time_passed < timedelta(seconds=time_frame):
                        if user.access_count >= max_calls:
                            remaining_time = timedelta(seconds=time_frame) - time_passed
                            update.message.reply_text(f"Rate limit exceeded. Please try again in "
                                                      f"{remaining_time.seconds} seconds.")
                            return
                        else:
                            user.access_count += 1
                    else:
                        user.last_access = current_time
                        user.access_count = 1

            return func(update, context, *args, **kwargs)
        return wrapper
    return decorator


@rate_limit(max_calls=3, time_frame=60)  # 3 calls per minute
def heavy_image_processing(update, context):
    # Your image processing code here
    update.message.reply_text("Image processed successfully!")


def main():
    updater = Updater("YOUR_BOT_TOKEN", use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("process_image", heavy_image_processing))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
