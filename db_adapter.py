from pony.orm import Database, Required, PrimaryKey, db_session
from datetime import datetime, timedelta
import asyncio
from telegram.ext import Application, CommandHandler

db = Database()

class User(db.Entity):
    id = PrimaryKey(int)
    last_access = Required(datetime)
    access_count = Required(int)

db.bind(provider='sqlite', filename='data/users.sqlite', create_db=True)
db.generate_mapping(create_tables=True)

async def check_rate_limit(user_id, max_calls, time_frame):
    current_time = datetime.now()

    def db_operation():
        with db_session:
            user = User.get(id=user_id)
            if user is None:
                User(id=user_id, last_access=current_time, access_count=0)
                return True
            else:
                time_passed = current_time - user.last_access
                if time_passed < timedelta(seconds=time_frame):
                    if user.access_count >= max_calls:
                        remaining_time = timedelta(seconds=time_frame) - time_passed
                        return remaining_time.seconds
                    else:
                        user.access_count += 1
                        return True
                else:
                    user.last_access = current_time
                    user.access_count = 1
                    return True

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, db_operation)