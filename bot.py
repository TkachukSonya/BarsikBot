import shutil
import os
import re
import telebot
import urllib.request
from PIL import Image, ImageFilter

TOKEN = '1159916736:AAGVKlGRzpHMgD6rp0PvWki12IzgSe7NEpg'
bot = telebot.TeleBot(TOKEN)

RESULT_STORAGE = 'photos'
PARAMS = dict()
faq1 = 'http://i.piccy.info/i9/6be3d3609a6548758d351063a94e3b1d/1590932041/175500/1381121/gaid_barsyk.jpg'

def get_image_id_from_message(message):
    return message.photo[len(message.photo) - 1].file_id


def save_image_from_message(message):
    image_id = get_image_id_from_message(message)
    file_path = bot.get_file(image_id).file_path

    image_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"

    image_name = f"{image_id}.png"
    urllib.request.urlretrieve(image_url, f"{RESULT_STORAGE}/{image_name}")
    return image_name


def cleanup_remove_images(image_name, image_name_new):
    os.remove(f'{RESULT_STORAGE}/{image_name}')
    os.remove(f'{RESULT_STORAGE}/{image_name_new}')


def clear_chat_info(chat_id):
    PARAMS[chat_id] = None


def get_image_capture_params(message):
    caption = message.caption

    if caption is not None:
        parsed_params = [param.strip() for param in re.split(r'\W+', caption.strip())]

        if len(parsed_params) == 2:
            params = dict()
            params['rgbmax'] = int(parsed_params[0]) if parsed_params[0].isdigit() and 0 <= int(parsed_params[0]) <= 255 else None
            params['rgbmin'] = int(parsed_params[-1]) if parsed_params[-1].isdigit() and 0 <= int(parsed_params[-1]) <= 255 else None
            if not None in [params['rgbmax'], params['rgbmin']]:
                return params

        bot.send_message(chat_id=message.chat.id, text=f'''Прости, но мне кажется, что мы разговариваем на разных языках
            \n❗️Воспользуйся командой /help, чтобы посмотреть как я работаю!''')
    return None


def handle_image(image_name, params):
    content_image = Image.open(f"{RESULT_STORAGE}/{image_name}")

    rgbmax = params['rgbmax']
    rgbmin = params['rgbmin']

    R, G, B = content_image.split()

    rout = R.point(lambda i: (i - rgbmin) / (rgbmax - rgbmin) * 255)
    gout = G.point(lambda i: (i - rgbmin) / (rgbmax - rgbmin) * 255)
    bout = B.point(lambda i: (i - rgbmin) / (rgbmax - rgbmin) * 255)

    result_img_pillow = Image.merge("RGB", (rout, gout, bout))
    image_name_new = "handled_image_" + image_name
    result_img_pillow.save(f"{RESULT_STORAGE}/{image_name_new}")
    return image_name_new


def process_image(message, image_name, params):
    contrast_image_filename = handle_image(image_name, params=params)

    bot.send_message(chat_id=message.chat.id, text='Получилось!')
    bot.send_photo(message.chat.id, open(f'{RESULT_STORAGE}/{contrast_image_filename}', 'rb'),
                   caption=f'😜 Это было круто! А хочешь еще несколько фото обработаем? Быстрее отправляй их мне!')

    # Clear
    cleanup_remove_images(image_name, contrast_image_filename)


@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, '''Привет-привет! ✌️ Я бот, чтобы обработать твои изображения!
    \nДавай начнем работу прямо сейчас! Отправь мне любое изображение!
    \nНо если вдруг ты не знаешь как правильно это сделать, загляни в команду /help, я тебе расскажу как я работаю!''')


@bot.message_handler(commands=['help'])
def help_message(message):
    bot.send_message(message.chat.id, '''Итак, как же я работаю? 
    \nЧтобы я обработал твои изображения, мне нужны будут:
    \n1️⃣ Само изображение;
    \n2️⃣ Чтобы ты ввел номер от 0 до 255 первый раз
    \n3️⃣ И чтобы ты ввел номер от 0 до 255 второй раз. Всё просто!
    \nНо ты спросишь - зачем? Дело в том, что я умный бот, и работаю тоже по умному! Когда ты загружаешь изображение, то
     я, когда прошу тебя ввести значения. Когда ты их ввел, я устанавливаю их и обрабатываю фото соответственно. 
     Твое первое значени - самая тёмная точка, а второе - самое светлая. 
    \n❗️ Чем больше разница между первым и вторым значением, тем менее контрастно твое фото будет в итоге.
    \nК примеру, это должно быть что-то вроде 230 15. Вроде бы всё понятно! А если нет, то посмотри картинку ниже, там 
    всё показано!
    \nАх да, чуть не забыл. Запомни, первое значение обязательно должно быть больше!''')
    bot.send_photo(message.chat.id, faq1)


@bot.message_handler(content_types=['text'])
def handle_text(message):
    cid = message.chat.id

    if PARAMS.get(cid) is not None:
        if message.text.isdigit():
            number = int(message.text)
            if 0 <= number <= 255:
                if PARAMS[cid].get('rgbmax') is None:
                    PARAMS[cid]['rgbmax'] = number
                    bot.send_message(chat_id=cid, text='Супер, у тебя всё получилось, а теперь введи еще раз '
                                                       'значение от 0 до 255')
                else:
                    PARAMS[cid]['rgbmin'] = number
                    process_image(message, image_name=PARAMS[cid]['image'], params=PARAMS[cid])
                    clear_chat_info(cid)
            else:
                bot.send_message(chat_id=cid, text='Ой, что-то пошло не так... 🤷‍♂️Введи, пожалуйста'
                                                   'значение от 0 до 255')
        else:
            bot.send_message(chat_id=cid, text='🤷‍♂️Прости, но я не такой умный, чтобы понять тебя. Лучше отправь '
                                               'число')
    else:
        bot.send_message(chat_id=cid, text='Наверное, ты забыл загрузить изображение 💁‍♂️ Давай исправим это')


@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    cid = message.chat.id

    image_name = save_image_from_message(message)
    bot.send_message(chat_id=cid, text='Отлично, я сохранил твою фотку!')

    PARAMS[cid] = {
             'image': image_name
         }
    bot.send_message(chat_id=message.chat.id, text='Если ты уже ознакомился с инструкцией, то давай начнем '
                                                        'немедленно! Отправь мне значение от 0 до 255:')


if __name__ == '__main__':
    try:
        if not os.path.exists(RESULT_STORAGE):
            os.makedirs(RESULT_STORAGE)
        bot.polling()
    except Exception as e:
        print(e)
    finally:
        if os.path.exists(RESULT_STORAGE):
            shutil.rmtree(RESULT_STORAGE)
