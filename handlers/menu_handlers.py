from asyncio.tasks import sleep
from datetime import datetime
from typing import Union

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
from aiogram.types import CallbackQuery, Message

from data.config import ADMIN_ID
from data.loader import dp, bot
from handlers.admin_handlers import admin_base_change, admin_panel, credit_mutation_abc
# , enter_name, enter_price, mutation
from keyboard.inline.choice_buttons import start_keyboard, dishes_menu_keyboard, approval_keyboard, \
    admin_start_keyboard, dishes_menu_approve_keyboard
from utils import database, states
from utils.order_to_sheets import add_order_to_sheet, create_new_sheet, get_order_from_sheet, cancel_order

db = database.DBCommands()


@dp.message_handler(Command('start', prefixes='/'))
async def registration_start(message: Message, state: FSMContext):
    old_customer = await db.get_customer(message.from_user.id)
    if old_customer:
        return
    await states.RegMenu.reg_name.set()
    order: dict = await state.get_data()
    text = 'Введи имя'
    order_message = await message.answer(text=text)
    order.update({'order_message': [order_message]})
    await state.set_data(order)


@dp.message_handler(regexp=r"^([А-Я,а-я-Ёё]+)$", state=states.RegMenu.reg_name)
async def registration(message: Message, state: FSMContext):
    order: dict = await state.get_data()
    await delete_messages(state=state)
    name = message.text
    order.update({'name': name})
    text = 'Введи фамилию'
    order_message = await message.answer(text=text)
    order.update({'order_message': [order_message]})
    await state.set_data(order)
    await states.RegMenu.reg_surname.set()


@dp.message_handler(regexp=r"^([А-Я,а-я-Ёё]+)$", state=states.RegMenu.reg_surname)
async def registration_fin(message: Message, state: FSMContext):
    order: dict = await state.get_data()
    surname: str = message.text
    name: str = order.pop('name')
    pseudonym = f'{surname.capitalize()} {name.capitalize()}'
    await delete_messages(state=state)
    customer = message.from_user
    await db.add_new_customer(customer=customer, customer_pseudonym=pseudonym)
    text = f'Вы зарегистрировались под именем:\n\n{pseudonym}'
    await message.answer(text=text)
    await state.reset_state()


@dp.message_handler(state=[states.RegMenu.reg_name, states.RegMenu.reg_surname])
async def wrong(message: Message, state: FSMContext):
    current_state = await state.get_state()
    name = 'фамилию'
    if current_state == 'RegMenu:reg_name':
        name = 'имя'
    text = f'Не верный формат ввода, попробуй ещё раз ввести {name} кириллицей без пробелов'
    await message.answer(text=text)
    await message.delete()


@dp.message_handler(Command(['menu', 'еню'], prefixes=['/', 'М']), state='*')
@dp.throttled(rate=2)
async def menu_command(message: types.Message, state: FSMContext):
    old_customer = await db.get_customer(message.from_user.id)
    if old_customer:
        # data = {'order':{}, 'cust':{}}
        # await state.set_data(data)
        # data: dict = await state.get_data()
        # print(data)
        # order: dict = data['order']
        # order.update({'llkdjf':3321})
        # await state.set_data(order)
        # data: dict = await state.get_data()
        # print(data)
        # order: dict = await state.get_data()
        await delete_messages(state=state)
        await state.reset_state()
        await start_choice(message, state)
    else:
        await registration_start(message=message, state=state)


# @dp.callback_query_handler(text_contains='start_menu', state=states.Order.dishes_dict)
# async def to_start(call: CallbackQuery, state: FSMContext):
#     await state.reset_state()
#     await start_choice(call)


async def start_choice(message: Union[CallbackQuery, Message], state: FSMContext):
    await states.Order.main.set()
    markup = await start_keyboard()
    order: dict = await state.get_data()
    text = '"Меню блюд"-для выбора блюд\n "Инфо"-для просмотра команд'
    if message.from_user.id == int(ADMIN_ID):
        markup = await admin_start_keyboard()
        text = '"Панель администратора"-для входа в панель администратора\n ' \
               '"Меню блюд"-для выбора блюд\n "Инфо"-для просмотра команд'
    if isinstance(message, Message):
        order_message = await message.answer(text=text, reply_markup=markup)
    if isinstance(message, CallbackQuery):
        await bot.answer_callback_query(message.id)
        order_message = await message.message.edit_text(text=text, reply_markup=markup)
    order.update({'order_message': [order_message]})
    await state.set_data(order)


@dp.callback_query_handler(text_contains='info', state=states.Order.main)
async def info(call: CallbackQuery):
    await bot.answer_callback_query(call.id)
    print(2)


@dp.callback_query_handler(text_contains='dish_menu', state=states.Order.dishes_dict)
@dp.callback_query_handler(text_contains='dish_menu', state=states.Order.main)
async def dishes_choice(call: CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(call.id)
    order: dict = await state.get_data()
    db_dishes = await db.get_dishes()
    mutate_message = order.pop('order_message', None)
    if mutate_message:
        try:
            await mutate_message[0].delete()
        except:
            pass

    try:
        await call.message.delete()
    except:
        pass
    for dish in db_dishes:
        markup = await dishes_menu_keyboard(dish.name)
        order_dish = order.get(dish.name)
        quantity = None
        if order_dish:
            quantity = order_dish[1]
        if quantity:
            text_item = f'{dish.name}: {dish.price}грн. ✅ x {quantity}'
        else:
            text_item = f'{dish.name}: {dish.price} грн.'
        menu_message = await call.message.answer(text=text_item, reply_markup=markup)
        order.update({f'{dish.name}': [menu_message, quantity, dish.price]})

    order_string = ''
    total = 0
    for k, v in order.items():
        quantity = v[1]
        if quantity:
            dish = get_dish_from_list(db_dishes=db_dishes, dish=k)
            order_string += f'{k} {dish.price}x{quantity}: {dish.price * quantity}грн.\n'
            total += dish.price * quantity
    text = f'Ваш выбор \n\n{order_string}\nИтоговая стоимость {total} грн.'
    markup1 = await dishes_menu_approve_keyboard()
    order_message = await call.message.answer(text=text, reply_markup=markup1)
    order.update({'order_message': [order_message]})

    await state.set_data(order)
    await states.Order.dishes_dict.set()


@dp.callback_query_handler(text_contains='plus', state=states.Order.dishes_dict)
async def plus(call: CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(call.id)
    call_dish = call.data[4:]
    markup = await dishes_menu_keyboard(call_dish)
    order: dict = await state.get_data()
    call_list = order.get(call_dish)
    call_quantity = call_list[1]
    call_price = call_list[2]
    if call_quantity:
        call_quantity += 1
    else:
        call_quantity = 1
    text_item = f'{call_dish}: {call_price}грн. ✅ x {call_quantity}'
    call_list[1] = call_quantity
    order.update({f'{call_dish}': call_list})
    await call.message.edit_text(text=text_item, reply_markup=markup)
    await state.set_data(order)
    await mutate_order_message(state=state)


@dp.callback_query_handler(text_contains='minus', state=states.Order.dishes_dict)
async def minus(call: CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(call.id)
    call_dish = call.data[5:]
    markup = await dishes_menu_keyboard(call_dish)
    order: dict = await state.get_data()
    call_list = order.get(call_dish)
    call_quantity = call_list[1]
    call_price = call_list[2]
    if call_quantity and call_quantity > 1:
        call_quantity -= 1
        text_item = f'{call_dish}: {call_price}грн. ✅ x {call_quantity}'
    elif call_quantity is None or call_quantity <= 1:
        call_quantity = 0
        text_item = f'{call_dish}: {call_price}грн.'
    call_list[1] = call_quantity
    order.update({f'{call_dish}': call_list})
    await call.message.edit_text(text=text_item, reply_markup=markup)
    await state.set_data(order)
    await mutate_order_message(state=state)


async def mutate_order_message(state: FSMContext):
    order: dict = await state.get_data()
    mutate_message = order.pop('order_message')
    order_string = ''
    total = 0
    for k, v in order.items():
        quantity = v[1]
        if quantity:
            price = v[2]
            order_string += f'{k} {price}x{quantity}: {price * quantity}грн.\n'
            total += price * quantity
    text = f'Ваш выбор \n\n{order_string}\nИтоговая стоимость {total} грн.'
    markup1 = await dishes_menu_approve_keyboard()
    await mutate_message[0].edit_text(text=text, reply_markup=markup1)


@dp.callback_query_handler(text_contains='approve', state=states.Order.dishes_dict)
async def approve(call: CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(call.id)
    db_dishes = await db.get_dishes()
    customer = await db.get_customer(call.from_user.id)
    date: str = datetime.now().date().strftime('%d %m %Y')
    order: dict = await state.get_data()
    mutate_message = order.pop('order_message')
    markup = await approval_keyboard()

    order_string = ''
    total = 0
    for k, v in order.items():
        quantity = v[1]
        if quantity:
            dish = get_dish_from_list(db_dishes=db_dishes, dish=k)
            order_string += f'{k} {dish.price}x{quantity}: {dish.price * quantity}грн.\n'
            total += dish.price * quantity
        message = v[0]
        await message.delete()
    text = f'Ваш выбор \n\n{order_string}\nИтоговая стоимость {total} грн.'
    if customer.current_order == 1:
        current_order_dict = get_order_from_sheet(pseudonym=customer.pseudonym, date=date, dishes=db_dishes)
        current_order_string = ''
        current_total = 0
        for d, q in current_order_dict.items():
            if q:
                dish = get_dish_from_list(db_dishes=db_dishes, dish=d)
                current_order_string += f'{d} {dish.price}x{q}: {dish.price * q}грн.\n'
                current_total += dish.price * q
        text = f'Вы уже сделали заказ сегодня\nПодтвердите, чтобы отменить текущий заказ и принять новый\n❌\n' \
               f'{current_order_string}Итоговая стоимость {current_total} грн.\n\n✅\n'+text
    # todo pygsheets.exceptions.WorksheetNotFound
    await mutate_message[0].edit_text(text=text, reply_markup=markup)
    await states.Order.checkout.set()


@dp.callback_query_handler(text_contains='checkout', state=states.Order.checkout)
async def fin_approve(call: CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(call.id)
    date: str = datetime.now().date().strftime('%d %m %Y')
    dishes = await db.get_dishes()
    order: dict = await state.get_data()
    customer = await db.get_customer(call.from_user.id)
    if customer.current_order == 1:
        credit_back = cancel_order(pseudonym=customer.pseudonym, date=date, dishes=dishes)
        await db.credit_up(customer_id=customer.customer_id, val=credit_back)
    credit = add_order_to_sheet(customer=customer, date=date, order=order, dishes=dishes)
    await db.credit_down(customer_id=customer.customer_id, val=credit)
    await db.set_current_order(customer=customer)

    await state.reset_state()
    await call.message.delete()


@dp.callback_query_handler(text_contains='cancel', state='*')
@dp.throttled(rate=0.5)
async def cancel(call: Union[CallbackQuery, Message], state: FSMContext):
    current_state = await state.get_state()
    if current_state == 'Order:dishes_dict':
        order: dict = await state.get_data()
        order.pop('order_message', None)
        await state.set_data(order)
        await delete_messages(state=state)
        await state.reset_state()
        return await start_choice(message=call, state=state)
    if current_state == 'Order:checkout':
        await call.message.delete()
        await states.Order.dishes_dict.set()
        return await dishes_choice(call=call, state=state)
    if current_state == 'AdminMenu:change':
        await state.reset_state()
        return await admin_panel(call=call, state=state)
    if current_state == 'AdminMenu:panel':
        await state.reset_state()
        return await start_choice(message=call, state=state)
    if current_state == 'AdminMenu:credit':
        await state.reset_state()
        return await admin_panel(call=call, state=state)
    if current_state == 'AdminMenu:credit_push':
        await state.reset_state()
        return await credit_mutation_abc(call=call, state=state)
    if current_state == 'AdminMenu:credit_upd':
        await state.reset_state()
        return await credit_mutation_abc(call=call, state=state)
    if current_state == 'AdminMenu:cancel':
        await state.reset_state()
        return await credit_mutation_abc(call=call, state=state)
    if current_state == 'ChangeItem:item':
        await states.AdminMenu.panel.set()
        return await admin_base_change(call=call, state=state)
    # if current_state == 'NewItem:price':
    #     await states.AdminMenu.change.set()
    #     await enter_name(call=call, state=state)
    if current_state == 'NewItem:name':
        await state.reset_state()
        await states.AdminMenu.panel.set()
        return await admin_base_change(call=call, state=state)
    # if current_state == 'NewItem:approve':
    #     await states.NewItem.name.set()
    #     await enter_price(message=call, state=state)
    # if current_state == 'ChangeItem:price':
    #     await states.ChangeItem.item.set()
    #     await mutation(call=call, state=state)
    # if current_state == 'ChangeItem:name':
    #     await states.ChangeItem.item.set()
    #     await mutation(call=call, state=state)
    if current_state == 'AdminMenu:instance_menu':
        await state.reset_state()
        return await admin_panel(call=call, state=state)
    if not current_state:
        return await start_choice(message=call, state=state)


async def delete_messages(state):
    order: dict = await state.get_data()
    order.pop('customers_data', None)
    for k, v in order.items():
        message = v[0]
        try:
            await message.delete()
        except:
            pass


def get_dish_from_list(db_dishes, dish):
    for d in db_dishes:
        if d.name == dish:
            return d


# todo aiogram.utils.exceptions.MessageNotModified
# todo raise WorksheetNotFound
