import re

from datetime import datetime
from typing import Union

from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.exceptions import MessageToEditNotFound

from data.loader import dp, bot
from keyboard.inline.choice_buttons import admin_panel_keyboard, \
    cancel_keyboard, approval_keyboard, credit_mutation_abc_keyboard, \
    credit_names_keyboard
from utils import database, states
from utils.database import Dish, Customer
from utils.order_to_sheets import create_new_sheet, get_rollback, delete_worksheet

db = database.DBCommands()


@dp.callback_query_handler(text_contains='admin_panel', state=states.Order.main)
async def admin_panel(call: CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(call.id)
    markup = await admin_panel_keyboard()
    text = 'Выбери дальнейшее действие'
    await call.message.edit_text(text=text, reply_markup=markup)
    await states.AdminMenu.panel.set()


@dp.callback_query_handler(text_contains='approve', state=states.AdminMenu.instance_menu)
@dp.callback_query_handler(text_contains='db_mutation', state=states.AdminMenu.panel)
async def admin_base_change(call: CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(call.id)
    current_state = await state.get_state()
    date = datetime.now().date()
    try:
        menu_date = await db.get_menu_date()
    except AttributeError:
        menu_date = ''
    order: dict = await state.get_data()
    menu_is_instance = date == menu_date
    if menu_is_instance & (current_state != 'AdminMenu:instance_menu'):
        markup = await approval_keyboard()
        text = f'Меню за {date.strftime("%d %m %Y")} уже загружено. \nХотите заменить меню?'
        current_message = await call.message.edit_text(text=text, reply_markup=markup)
        order.update({'order_message': [current_message]})
        await state.set_data(order)
        await states.AdminMenu.instance_menu.set()
        return
    markup = await cancel_keyboard()
    text = 'Отправь меню'
    current_message = await call.message.edit_text(text=text, reply_markup=markup)
    order.update({'order_message': [current_message]})
    await state.set_data(order)
    if current_state == 'AdminMenu:instance_menu':
        await states.AdminMenu.rollback.set()
        return
    await states.AdminMenu.change.set()


@dp.message_handler(state=states.AdminMenu.rollback)
@dp.message_handler(state=states.AdminMenu.change)
async def menu_parsing(message: Message, state: FSMContext):
    markup = await cancel_keyboard()
    food_list = [s.strip() for s in message.text.split('\n') if len(s.strip()) > 0]
    check_food_list = [s for s in food_list if not re.match(r'(^.+)( \d+)$', s)]
    order: dict = await state.get_data()
    if len(check_food_list) == 0:
        current_state = await state.get_state()
        date = datetime.now().date()
        date_str = date.strftime('%d %m %Y')
        if current_state == 'AdminMenu:rollback':
            rollback_dict = get_rollback(date=date_str)
            if rollback_dict:
                for p, c in rollback_dict.items():
                    customer = await db.credit_up(p, c)
                    text = f'{p}, твой сегодняшний заказ был отменен, на счет было возвращено {c} грн.'
                    await bot.send_message(chat_id=customer.customer_id, text=text)
            delete_worksheet(date_str)
        await db.del_dish_table()
        update_strings = ''
        for food_string in food_list:
            item_list = re.split(r' (?=\d+$)', food_string)
            new_item = Dish()
            new_item.date = date
            new_item.name = item_list[0]
            new_item.price = int(item_list[1])
            await new_item.create()
            update_strings += f'{item_list[0]} {item_list[1]} грн.\n'
        mutate_message: Message = order.pop('order_message')[0]
        text = f'Новое меню:\n{update_strings}'
        await mutate_message.edit_text(text=text)

        customers = await db.get_customers()
        dishes = await db.get_dishes()
        create_new_sheet(date=date_str, customers=customers, dishes=dishes)
        await db.cancel_current_order()

        await message.delete()
        await state.reset_state()
    else:
        mutate_message: Message = order.pop('order_message')[0]
        wrong_strings = ''
        for string in check_food_list:
            wrong_strings += f'{string}\n'
        text = f'Не все строки имеют верный формат\n{wrong_strings}'
        current_message = await mutate_message.edit_text(text=text, reply_markup=markup)
        order.update({'order_message': [current_message]})
        await message.delete() # todo MessageNotModified


@dp.callback_query_handler(text_contains='credit_mutation', state=states.AdminMenu.panel)
async def credit_mutation_abc(call: Union[Message, CallbackQuery], state: FSMContext):
    text = 'Выбери букву соответствующую первой букве фамилии гостя для зачисления оплаты'
    db_customers = await db.get_customers()
    dict_customers = {}
    for c in db_customers:
        c: Customer
        dict_customers.setdefault(c.pseudonym[:1].upper(), {}).update({c.pseudonym: c})
    markup = await credit_mutation_abc_keyboard(dict_customers)
    try:
        if isinstance(call, CallbackQuery):
            current_message = await call.message.edit_text(text=text, reply_markup=markup)
        elif isinstance(call, Message):
            current_message = await call.edit_text(text=text, reply_markup=markup)
    except MessageToEditNotFound:
        if isinstance(call, CallbackQuery):
            current_message = await call.message.answer(text=text, reply_markup=markup)
        elif isinstance(call, Message):
            current_message = await call.answer(text=text, reply_markup=markup)

    customers_data = await state.get_data()
    customers_data.update({'customers_data': dict_customers})
    customers_data.update({'order_message': [current_message]})
    await state.set_data(customers_data)
    await states.AdminMenu.credit.set()


@dp.callback_query_handler(text_contains='letter', state=states.AdminMenu.credit)
async def credit_names_to_list(call: CallbackQuery, state: FSMContext):
    data: dict = await state.get_data()
    customers_by_letter: dict = data['customers_data'][call.data[6:]]
    markup = await credit_names_keyboard(customers_by_letter)
    text = 'Выбери гостя для зачисления оплаты'

    current_message = await call.message.edit_text(text=text, reply_markup=markup)

    data.update({'customers_data': customers_by_letter})
    data.update({'order_message': [current_message]})
    await state.set_data(data)

    await states.AdminMenu.credit_push.set()


@dp.callback_query_handler(text_contains='push', state=states.AdminMenu.credit_push)
async def push_credits(call: CallbackQuery, state: FSMContext):
    data: dict = await state.get_data()
    customer = data['customers_data'][call.data[4:]]
    markup = await cancel_keyboard()
    text = f'Отправь сумму для зачисления на счет <b>{customer.pseudonym}</b>. \nТекущий баланс: <b>{customer.credit}</b> грн.'

    current_message = await call.message.edit_text(text=text, reply_markup=markup, parse_mode='HTML')
    data.update({'customers_data': customer})
    data.update({'order_message': [current_message]})
    await state.set_data(data)

    await states.AdminMenu.credit_upd.set()


@dp.message_handler(state=states.AdminMenu.credit_upd)
async def credit_update(message: Message, state: FSMContext):
    markup = await cancel_keyboard()
    string = message.text
    string_is_match = re.fullmatch(r'([+-]?\d+)', string)
    data: dict = await state.get_data()

    if string_is_match:
        customer: Customer.customer_id = data['customers_data']
        text = f'Пользователю <b>{customer.pseudonym}</b> было зачислено: <b>{string}</b> грн.'
        mutate_message: Message = data.pop('order_message')[0]

        await db.credit_up(customer_id=customer.customer_id, val=int(string))
        await message.delete()
        await mutate_message.edit_text(text=text, parse_mode='HTML')
        await credit_mutation_abc(call=message, state=state)
    else:
        mutate_message: Message = data.pop('order_message')[0]
        await mutate_message.delete()

        text = f'Не верный формат, отправь целое число'
        current_message = await message.answer(text=text, reply_markup=markup)
        data.update({'order_message': [current_message]})

        await message.delete()
        await state.set_data(data)


def get_dish_from_list(db_dishes, dish):
    for d in db_dishes:
        if d.name == dish:
            return d
