from datetime import datetime
from typing import Union

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
from aiogram.types import CallbackQuery, Message
from pygsheets import WorksheetNotFound

from data.config import ADMIN_ID
from data.loader import dp, bot
from handlers.admin_handlers import admin_panel, credit_mutation_abc
from keyboard.inline.choice_buttons import start_keyboard, dishes_menu_keyboard, approval_keyboard_reverse, \
    admin_start_keyboard, approval_keyboard, cancel_keyboard
from utils import database, states
from utils.database import Customer
from utils.order_to_sheets import add_order_to_sheet, get_order_from_sheet, cancel_order, \
    update_worksheet_pseudonym

db = database.DBCommands()


@dp.message_handler(Command('start', prefixes='/'))
async def registration_start(message: Message, state: FSMContext):
    old_customer = await db.get_customer(message.from_user.id)
    if old_customer:
        return
    await states.RegMenu.reg_name.set()
    await registration_name(message=message, state=state)


async def registration_name(message: Union[Message, CallbackQuery], state):
    order: dict = await state.get_data()
    text = 'Введи имя'
    if isinstance(message, Message):
        order_message = await message.answer(text=text)
    elif isinstance(message, CallbackQuery):
        order_message = await message.message.edit_text(text=text)
    order.update({'order_message': [order_message]})
    await state.set_data(order)


@dp.message_handler(regexp=r"^([А-Я,а-я-Ёё]+)$", state=[states.RegMenu.reg_name, states.ChangePseudonym.name])
async def registration(message: Message, state: FSMContext):
    order: dict = await state.get_data()
    await delete_messages(state=state)
    name = message.text
    order.update({'name': name})
    text = 'Введи фамилию'
    order_message = await message.answer(text=text)
    order.update({'order_message': [order_message]})
    await state.set_data(order)
    current_state = await state.get_state()
    if current_state == 'RegMenu:reg_name':
        await states.RegMenu.reg_surname.set()
    else:
        await states.ChangePseudonym.surname.set()


@dp.message_handler(regexp=r"^([А-Я,а-я-Ёё]+)$", state=[states.RegMenu.reg_surname, states.ChangePseudonym.surname])
async def registration_fin(message: Message, state: FSMContext):
    order: dict = await state.get_data()
    surname: str = message.text
    name: str = order.pop('name')
    date = datetime.now().date()
    date_str = date.strftime('%d %m %Y')
    pseudonym = f'{surname.capitalize()} {name.capitalize()}'
    await delete_messages(state=state)
    customer = message.from_user
    current_state = await state.get_state()

    if current_state == 'RegMenu:reg_surname':
        await db.add_new_customer(customer=customer, customer_pseudonym=pseudonym)
    else:
        old_customer: Customer = await db.get_customer(customer.id)
        menu_date = await db.get_menu_date()
        menu_is_instance = date == menu_date
        if old_customer:
            if menu_is_instance:
                try:
                    update_worksheet_pseudonym(old_pseudonym=old_customer.pseudonym, new_pseudonym=pseudonym, date=date_str)
                except WorksheetNotFound:
                    pass
            await db.update_pseudonym(customer=old_customer, pseudonym=pseudonym)
        else:
            return
    text = f'Вы зарегистрировались под именем:\n\n{pseudonym}'
    await message.answer(text=text, disable_notification=True)
    await state.reset_state()


@dp.message_handler(state=[states.RegMenu.reg_name, states.RegMenu.reg_surname,
                           states.ChangePseudonym.name, states.ChangePseudonym.surname])
async def wrong(message: Message, state: FSMContext):
    current_state = await state.get_state()
    order: dict = await state.get_data()
    name = 'фамилию'
    if current_state == 'RegMenu:reg_name' or current_state == 'ChangePseudonym:name':
        name = 'имя'
    text = f'Не верный формат ввода, попробуй ещё раз ввести {name} кириллицей без пробелов'
    order_message = await message.answer(text=text)
    order.update({'order_message': [order_message]})
    await state.set_data(order)
    await message.delete()


@dp.message_handler(Command(['menu', 'еню'], prefixes=['/', 'М']), state='*')
@dp.throttled(rate=2)
async def menu_command(message: types.Message, state: FSMContext):
    old_customer = await db.get_customer(message.from_user.id)
    if old_customer:
        await delete_messages(state=state)
        await state.reset_state()
        await start_choice(message, state)
        await message.delete()
    else:
        await registration_start(message=message, state=state)
        await message.delete()


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
        order_message = await message.answer(text=text, reply_markup=markup, disable_notification=True)
    if isinstance(message, CallbackQuery):
        await bot.answer_callback_query(message.id)
        order_message = await message.message.edit_text(text=text, reply_markup=markup)
    order.update({'order_message': [order_message]})
    await state.set_data(order)


@dp.callback_query_handler(text_contains='info', state=states.Order.main)
async def info(call: CallbackQuery, state=FSMContext):
    await bot.answer_callback_query(call.id)
    markup = await cancel_keyboard()
    data: dict = await state.get_data()
    await states.Order.info.set()

    text = '/change_reg_name'
    order_message = await call.message.edit_text(text=text, reply_markup=markup)

    data.update({'order_message': [order_message]})
    await state.set_data(data)


@dp.callback_query_handler(text_contains='dish_menu', state=states.Order.dishes_dict)
@dp.callback_query_handler(text_contains='dish_menu', state=states.Order.main)
async def dishes_choice(call: CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(call.id)

    menu_date = await db.get_menu_date()
    date = datetime.now().date()
    menu_is_instance = date == menu_date

    if menu_is_instance:
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
            markup = await dishes_menu_keyboard(dish_id=dish.id)
            order_dish = order.get(dish.id)
            quantity = None
            if order_dish:
                quantity = order_dish[1]
            if quantity:
                text_item = f'{dish.name}: {dish.price}грн. ✅ x {quantity}'
            else:
                text_item = f'{dish.name}: {dish.price} грн.'
            menu_message = await call.message.answer(text=text_item, reply_markup=markup, disable_notification=True)
            order.update({dish.id: [menu_message, quantity, dish.price, dish.name]})

        order_string = ''
        total = 0
        for k, v in order.items():
            quantity = v[1]
            if quantity:
                dish = get_dish_from_list_by_id(db_dishes=db_dishes, dish_id=k)
                order_string += f'{v[3]} {dish.price}x{quantity}: {dish.price * quantity}грн.\n'
                total += dish.price * quantity
        text = f'Ваш выбор \n\n{order_string}\nИтоговая стоимость {total} грн.'
        markup1 = await approval_keyboard()
        order_message = await call.message.answer(text=text, reply_markup=markup1, disable_notification=True)
        order.update({'order_message': [order_message]})

        await state.set_data(order)
        await states.Order.dishes_dict.set()
    else:
        markup = await cancel_keyboard()
        text = f'Меню на <b>{date.strftime("%d.%m.%Y")}</b> еще <b>не готово</b>, попробуйте немного позже'
        await call.message.edit_text(text=text, reply_markup=markup, parse_mode='HTML')
        await states.Order.dishes_dict.set()


@dp.callback_query_handler(text_contains='plus', state=states.Order.dishes_dict)
async def plus(call: CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(call.id)
    call_dish = int(call.data[4:])
    markup = await dishes_menu_keyboard(call_dish)
    order: dict = await state.get_data()
    call_list = order.get(call_dish)
    call_quantity = call_list[1]
    call_price = call_list[2]
    if call_quantity:
        call_quantity += 1
    else:
        call_quantity = 1
    text_item = f'{call_list[3]}: {call_price}грн. ✅ x {call_quantity}'
    call_list[1] = call_quantity
    order.update({call_dish: call_list})
    await call.message.edit_text(text=text_item, reply_markup=markup)
    await state.set_data(order)
    await mutate_order_message(state=state)


@dp.callback_query_handler(text_contains='minus', state=states.Order.dishes_dict)
async def minus(call: CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(call.id)
    call_dish = int(call.data[5:])
    markup = await dishes_menu_keyboard(call_dish)
    order: dict = await state.get_data()
    call_list = order.get(call_dish)
    call_quantity = call_list[1]
    call_price = call_list[2]
    if call_quantity and call_quantity > 1:
        call_quantity -= 1
        text_item = f'{call_list[3]}: {call_price}грн. ✅ x {call_quantity}'
    elif call_quantity is None or call_quantity <= 1:
        call_quantity = 0
        text_item = f'{call_list[3]}: {call_price}грн.'
    call_list[1] = call_quantity
    order.update({call_dish: call_list})
    await call.message.edit_text(text=text_item, reply_markup=markup)
    await state.set_data(order)
    await mutate_order_message(state=state)


async def mutate_order_message(state: FSMContext):
    order: dict = await state.get_data()
    mutate_message = order.pop('order_message')
    order_string = ''
    total = 0
    for _, v in order.items():
        quantity = v[1]
        if quantity:
            price = v[2]
            dish_name = v[3]
            order_string += f'{dish_name} {price}x{quantity}: {price * quantity}грн.\n'
            total += price * quantity
    text = f'Ваш выбор \n\n{order_string}\nИтоговая стоимость {total} грн.'
    markup1 = await approval_keyboard()
    await mutate_message[0].edit_text(text=text, reply_markup=markup1)


@dp.callback_query_handler(text_contains='approve', state=states.Order.dishes_dict)
async def approve(call: CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(call.id)
    db_dishes = await db.get_dishes()
    customer = await db.get_customer(call.from_user.id)
    date: str = datetime.now().date().strftime('%d %m %Y')
    order: dict = await state.get_data()
    mutate_message = order.pop('order_message')
    markup = await approval_keyboard_reverse()

    order_string = ''
    total = 0
    for k, v in order.items():
        quantity = v[1]
        if quantity:
            dish_name = v[3]
            dish = get_dish_from_list_by_id(db_dishes=db_dishes, dish_id=k)
            order_string += f'{dish_name} {dish.price}x{quantity}: {dish.price * quantity}грн.\n'
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
                dish = get_dish_from_list_by_name(db_dishes=db_dishes, dish=d)
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
    text = call.message.text
    await call.message.edit_text(text=text)


@dp.message_handler(Command(['change_reg_name'], prefixes='/'), state='*')
async def change_pseudonym(message: Message, state: FSMContext):
    await delete_messages(state=state)
    customer: Customer = await db.get_customer(message.from_user.id)
    if customer:
        markup = await approval_keyboard()
        text = f'Ты обнаружил ошибку в имени:\n{customer.pseudonym} ?\nЖелаешь изменить его?'
        await states.ChangePseudonym.initial.set()
        await message.delete()
        await message.answer(text=text, reply_markup=markup)
    else:
        await states.RegMenu.reg_name.set()
        await registration_name(message=message, state=state)


@dp.callback_query_handler(text_contains='approve', state=states.ChangePseudonym.initial)
async def to_reregistration(call: CallbackQuery, state=FSMContext):
    await states.ChangePseudonym.name.set()
    await registration_name(message=call, state=state)


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
    if current_state == 'AdminMenu:change' or current_state == 'AdminMenu:rollback':
        await state.reset_state()
        return await admin_panel(call=call, state=state)
    if current_state == 'AdminMenu:panel' or current_state == 'Order:info':
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
    if current_state == 'AdminMenu:instance_menu':
        await state.reset_state()
        return await admin_panel(call=call, state=state)
    if current_state == 'ChangePseudonym:initial':
        await state.reset_state()
        await call.message.delete()
        return
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


def get_dish_from_list_by_id(db_dishes, dish_id):
    for d in db_dishes:
        if d.id == dish_id:
            return d


def get_dish_from_list_by_name(db_dishes, dish):
    for d in db_dishes:
        if d.name == dish:
            return d


# todo aiogram.utils.exceptions.MessageNotModified
# todo raise WorksheetNotFound
