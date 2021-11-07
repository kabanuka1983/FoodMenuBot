import pygsheets
from pygsheets import SpreadsheetNotFound

from data.config import SERVICE_FILE, SHARE_ADDRESS, FILE_NAME

gc = pygsheets.authorize(service_file=SERVICE_FILE, scopes=('https://www.googleapis.com/auth/spreadsheets',
                                                            'https://www.googleapis.com/auth/drive'))


def create_file():
    if isinstance(SHARE_ADDRESS, list):
        adr_string = ''
        try:
            sh = gc.open(title=FILE_NAME)
            for adr in SHARE_ADDRESS:
                sh.share(email_or_domain=adr, role='writer')
                adr_string += f'{adr}\n'
            return f'Файл "{FILE_NAME}" открыт \nрасшарен для: \n{adr_string}'
        except SpreadsheetNotFound:
            sh = gc.create(title=FILE_NAME)
            for adr in SHARE_ADDRESS:
                sh.share(email_or_domain=adr, role='writer')
                adr_string += f'{adr}\n'
            return f'Файл "{FILE_NAME}" отсутствует и был создан \nрасшарен для: \n{adr_string}'
    if isinstance(SHARE_ADDRESS, str):
        try:
            sh = gc.open(title=FILE_NAME)
            sh.share(email_or_domain=SHARE_ADDRESS, role='writer')
            return f'Файл "{FILE_NAME}" открыт \nрасшарен для: \n{SHARE_ADDRESS}'
        except SpreadsheetNotFound:
            sh = gc.create(title=FILE_NAME)
            sh.share(email_or_domain=SHARE_ADDRESS, role='writer')
            return f'Файл "{FILE_NAME}" отсутствует и был создан \nрасшарен для: \n{SHARE_ADDRESS}'


def add_order_to_sheet(user, order: dict):
    values = [user]
    for k, v in order.items():
        value = f'{k} x {v}'
        values.append(value)
    sh = gc.open(FILE_NAME)
    wks = sh.worksheets()[-1]
    wks.insert_rows(row=0, number=2, values=[values])

# {'Сало': 1, 'Хлеб': 1, 'Рыба': 1}
