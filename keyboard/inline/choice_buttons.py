from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.callback_data import CallbackData


async def start_keyboard():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.row(InlineKeyboardButton(text='Меню блюд',
                                    callback_data='dish_menu'))
    markup.row(InlineKeyboardButton(text='Инфо',
                                    callback_data='info'))
    return markup


async def dishes_menu_keyboard(dish):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.row(InlineKeyboardButton(text='+', callback_data=f'plus{dish}'),
               InlineKeyboardButton(text='-', callback_data=f'minus{dish}'))
    return markup


async def dishes_menu_approve_keyboard():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.row(InlineKeyboardButton(text='Подтвердить', callback_data='approve'))
    markup.row(InlineKeyboardButton(text='⬅Назад', callback_data='cancel'))
    return markup


async def approval_keyboard():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.row(InlineKeyboardButton(text='⬅Назад',
                                    callback_data='cancel'))
    markup.row(InlineKeyboardButton(text='Подтвердить',
                                    callback_data='checkout'))
    return markup


async def admin_start_keyboard():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.row(InlineKeyboardButton(text='Панель администратора',
                                    callback_data='admin_panel'))
    markup.row(InlineKeyboardButton(text='Меню блюд',
                                    callback_data='dish_menu'))
    markup.row(InlineKeyboardButton(text='Инфо',
                                    callback_data='info'))
    return markup


async def admin_panel_keyboard():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.row(InlineKeyboardButton(text='Внести изменения в меню',
                                    callback_data='db_mutation'))
    markup.row(InlineKeyboardButton(text='⬅Назад',
                                    callback_data='cancel'))
    return markup


async def base_change_keyboard(db_dishes):
    markup = InlineKeyboardMarkup(row_width=1)
    for dish in db_dishes:
        text_button = f'{dish.name}: {dish.price} грн.'
        markup.insert(InlineKeyboardButton(text=text_button, callback_data=f'mutation{dish.name}'))
    markup.row(InlineKeyboardButton(text='Добавить блюдо в меню', callback_data='new_item'))
    markup.row(InlineKeyboardButton(text='⬅Назад', callback_data='cancel'))
    return markup


async def mutation_keyboard():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.row(InlineKeyboardButton(text='Изменить наименование', callback_data='name'))
    markup.row(InlineKeyboardButton(text='Изменить цену', callback_data='price'))
    markup.row(InlineKeyboardButton(text='Удалить', callback_data='delete'))
    markup.row(InlineKeyboardButton(text='⬅Назад', callback_data='cancel'))
    return markup


async def cancel_keyboard():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.row(InlineKeyboardButton(text='⬅Назад', callback_data='cancel'))
    return markup
# async def admin_panel_keyboard(db_dishes, order: dict):
#     markup = InlineKeyboardMarkup(row_width=1)
#     for dish in db_dishes:
#         quantity = order.get(dish.name)
#         if quantity:
#             text_button = f'{dish.name}: {dish.price / 100} грн. ✅ x {quantity}'
#         else:
#             text_button = f'{dish.name}: {dish.price/100} грн.'
#         markup.insert(InlineKeyboardButton(text=text_button, callback_data=f'dish_menu{dish.name}'))
#     markup.row(InlineKeyboardButton(text='Подтвердить выбор', callback_data='approve'))
#     markup.row(InlineKeyboardButton(text='⬅Назад/Сброс', callback_data='cancel'))
#
#     return markup

# menu_callback = CallbackData('menu', 'level', 'section_name', 'dishes')
#
#
# def make_menu_callback_data(level, section_name='0', dishes='0'):
#     return menu_callback.new(level=level, section_name=section_name, dishes=dishes)
#
#
# async def start_keyboard():
#     CURRENT_LEVEL = 0
#
#     markup = InlineKeyboardMarkup(row_width=1)
#     markup.row(InlineKeyboardButton(text='Меню блюд',
#                                     callback_data=make_menu_callback_data(level=CURRENT_LEVEL+1,
#                                                                           section_name='dish_menu')))
#     markup.row(InlineKeyboardButton(text='Инфо',
#                                     callback_data=make_menu_callback_data(level=CURRENT_LEVEL+1,
#                                                                           section_name='info')))
#     return markup
#
#
# async def dishes_menu_keyboard(section_name, db_dishes):
#     CURRENT_LEVEL = 1
#
#     markup = InlineKeyboardMarkup(row_width=1)
#
#     if section_name == 'info':
#         markup.row(InlineKeyboardButton(text='⬅Назад',
#                                         callback_data=make_menu_callback_data(level=CURRENT_LEVEL-1,)))
#     if section_name == 'dish_menu':
#         for dish in db_dishes:
#             text_button = f'{dish.name}: {dish.price/100} грн.'
#             markup.insert(InlineKeyboardButton(text=text_button,
#                                                callback_data=make_menu_callback_data(level=CURRENT_LEVEL,
#                                                                                      section_name=section_name)))
#         markup.row(InlineKeyboardButton(text='⬅Назад/Сброс',
#                                         callback_data=make_menu_callback_data(level=CURRENT_LEVEL-1)))
#
#     return markup
