import re

from asyncio.tasks import sleep
from datetime import datetime
from typing import Union

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
from aiogram.types import CallbackQuery, Message

from data.config import ADMIN_ID
from data.loader import dp, bot
from keyboard.inline.choice_buttons import admin_panel_keyboard, base_change_keyboard, mutation_keyboard, \
    cancel_keyboard, approval_keyboard, dishes_menu_approve_keyboard, credit_mutation_abc_keyboard, \
    credit_names_keyboard
from utils import database, states
from utils.database import Dish, Customer
from utils.order_to_sheets import create_new_sheet, rollback

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
        markup = await dishes_menu_approve_keyboard()
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
    check_food_list = [s for s in food_list if not re.match(r'[\s\w+]* \d+$', s)]
    order: dict = await state.get_data()
    if len(check_food_list) == 0:
        current_state = await state.get_state()
        date = datetime.now().date()
        date_str = date.strftime('%d %m %Y')
        # customers = await db.get_customers()
        # dishes = await db.get_dishes()
        if current_state == 'AdminMenu:rollback':
            rollback(date=date_str)
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
        await message.delete()


@dp.callback_query_handler(text_contains='credit_mutation', state=states.AdminMenu.panel)
async def credit_mutation_abc(call: CallbackQuery, state: FSMContext):
    text = 'Выбери букву соответствующую первой букве фамилии гостя для зачисления оплаты'
    db_customers = await db.get_customers()
    dict_customers = {}
    for c in db_customers:
        c: Customer
        dict_customers.setdefault(c.pseudonym[:1].upper(), {}).update({c.pseudonym: c})
    markup = await credit_mutation_abc_keyboard(dict_customers)
    current_message = await call.message.edit_text(text=text, reply_markup=markup)
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
    data.update({'customers_data': customers_by_letter})
    text = 'Выбери гостя для зачисления оплаты'
    current_message = await call.message.edit_text(text=text, reply_markup=markup)
    data.update({'order_message': [current_message]})
    await state.set_data(data)
    await states.AdminMenu.credit_push.set()


@dp.callback_query_handler(text_contains='push', state=states.AdminMenu.credit_push)
async def push_credits(call: CallbackQuery, state: FSMContext):
    data: dict = await state.get_data()
    customer = data['customers_data'][call.data[4:]]
    markup = await cancel_keyboard()
    data.update({'customers_data': customer})
    text = f'Отправь сумму для зачисления на счет <b>{customer.pseudonym}</b>. \nТекущий баланс: <b>{customer.credit}</b>'
    current_message = await call.message.edit_text(text=text, reply_markup=markup, parse_mode='HTML')
    data.update({'order_message': [current_message]})
    await state.set_data(data)
    await states.AdminMenu.credit_upd.set()


@dp.message_handler(state=states.AdminMenu.credit_upd)
async def credit_update(message: Message, state: FSMContext):
    string = message.text
    string_is_match = re.fullmatch(r'([+-]?\d+)', string)
    if string_is_match:
        data = await state.get_data()
        customer = data['customers_data']
        await db.credit_up(customer_id=customer.customer_id, val=int(string))
        text = f'Пользователю {customer.pseudonym} было зачислено{string}'
        await message



# @dp.callback_query_handler(text_contains='db_mutation', state=states.AdminMenu.panel)
# async def admin_base_change(call: Union[CallbackQuery, Message], state: FSMContext):
#     db_dishes = await db.get_dishes()
#     markup = await base_change_keyboard(db_dishes=db_dishes)
#     text = 'Выбери наименование для внесения изменений/удаления или добавьте новое'
#     if isinstance(call, CallbackQuery):
#         await bot.answer_callback_query(call.id)
#         await call.message.edit_text(text=text, reply_markup=markup)
#     if isinstance(call, Message):
#         await call.answer(text=text, reply_markup=markup)
#     await states.AdminMenu.change.set()


# @dp.callback_query_handler(text_contains='mutation', state=states.AdminMenu.change)
# async def mutation(call: CallbackQuery, state: FSMContext):
#     await bot.answer_callback_query(call.id)
#     db_dishes = await db.get_dishes()
#     markup = await mutation_keyboard()
#     call_dish = call.data[8:]
#     if call.data == 'cancel':
#         dish = await state.get_data()
#         call_dish = dish.name
#     dish = get_dish_from_list(db_dishes=db_dishes, dish=call_dish)
#     await state.set_data(dish)
#     text = f'Вы хотите внести изменения в \n{dish.name}: {dish.price} грн.\nили удалить его?'
#     await call.message.edit_text(text=text, reply_markup=markup)
#     await states.ChangeItem.item.set()
#
#
# @dp.callback_query_handler(text_contains='name', state=states.ChangeItem.item)
# @dp.callback_query_handler(text_contains='new_item', state=states.AdminMenu.change)
# async def enter_name(call: CallbackQuery, state: FSMContext):
#     current_state = await state.get_state()
#     markup = await cancel_keyboard()
#     text = 'Введите наименование нового блюда'
#     await bot.answer_callback_query(call.id)
#     if current_state == 'AdminMenu:change':
#         await states.NewItem.name.set()
#     if current_state == 'ChangeItem:item':
#         dish = await state.get_data()
#         await states.ChangeItem.name.set()
#         text = f'Вы хотите изменить: \n{dish.name} \nОтправьте новое наименование'
#     await call.message.delete()
#     await call.message.answer(text=text, reply_markup=markup)
#
#
# @dp.callback_query_handler(text_contains='price', state=states.ChangeItem.item)
# @dp.message_handler(state=states.NewItem.name)
# async def enter_price(message: Union[Message, CallbackQuery], state: FSMContext):
#     current_state = await state.get_state()
#     markup = await cancel_keyboard()
#     if current_state == 'NewItem:name':
#         if isinstance(message, Message):
#             name = message.text
#         if isinstance(message, CallbackQuery):
#             call_name = await state.get_data()
#             name = call_name.name
#         new_item = Dish()
#         new_item.name = name
#         await state.set_data(new_item)
#         await states.NewItem.price.set()
#     if current_state == 'ChangeItem:item':
#         dish = await state.get_data()
#         name = dish.name
#         await states.ChangeItem.price.set()
#     text = f'Введите стоимость \n{name}'
#     if isinstance(message, Message):
#         await message.answer(text=text, reply_markup=markup)
#     if isinstance(message, CallbackQuery):
#         await message.message.answer(text=text, reply_markup=markup)
#
#
# @dp.message_handler(regexp=r'^(\d+)$', state=states.NewItem.price)
# async def get_new_item(message: Message, state: FSMContext):
#     markup = await approval_keyboard()
#     price = message.text
#     new_item = await state.get_data()
#     new_item.price = int(price)
#     await state.set_data(new_item)
#     text = f'Вы хотите добавить: \n\n{new_item.name} {new_item.price} грн.'
#     await message.answer(text=text, reply_markup=markup)
#     await states.NewItem.approve.set()
#
#
# @dp.callback_query_handler(text_contains='checkout', state=states.NewItem.approve)
# async def add_new_item(call: CallbackQuery, state: FSMContext):
#     new_item = await state.get_data()
#     await new_item.create()
#     text = f'Вы добавили: \n{new_item.name}: {new_item.price}грн.'
#     await call.message.edit_text(text=text)
#     await sleep(2)
#     await states.AdminMenu.panel.set()
#     await admin_base_change(call=call, state=state)
#
#
# @dp.callback_query_handler(text_contains='delete', state=states.ChangeItem.item)
# async def delete_item(call: CallbackQuery, state: FSMContext):
#     dish = await state.get_data()
#     await db.delete_item(dish.name)
#     text = f'Вы удалили: \n{dish.name}: {dish.price} грн.'
#     await call.message.edit_text(text=text)
#     await sleep(2)
#     await states.AdminMenu.panel.set()
#     await admin_base_change(call=call, state=state)
#
#
# @dp.message_handler(state=states.ChangeItem.name)
# async def change_name(message: Message, state: FSMContext):
#     dish = await state.get_data()
#     new_name = message.text
#     await db.update_name(dish_name=dish.name, new_name=new_name)
#     text = f'Вы изменили \n{dish.name} \nна \n{new_name}'
#     await message.answer(text=text)
#     await sleep(2)
#     await states.AdminMenu.panel.set()
#     await admin_base_change(call=message, state=state)
#
#
# @dp.message_handler(regexp=r'^(\d+)$', state=states.ChangeItem.price)
# async def change_price(message: Message, state: FSMContext):
#     dish = await state.get_data()
#     new_price = int(message.text)
#     await db.update_price(dish.name, new_price)
#     text = f'Вы установили стоимость: \n{dish.name} \nв размере \n{new_price}грн.'
#     await message.answer(text=text)
#     await sleep(2)
#     await states.AdminMenu.panel.set()
#     await admin_base_change(call=message, state=state)
#
#
# @dp.message_handler(state=states.ChangeItem.price)
# @dp.message_handler(state=states.NewItem.price)
# async def not_quantity(message: Message):
#     await message.answer("Неверное значение, введите число")


def get_dish_from_list(db_dishes, dish):
    for d in db_dishes:
        if d.name == dish:
            return d
