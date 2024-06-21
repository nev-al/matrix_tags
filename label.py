from pylibdmtx import pylibdmtx
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, Frame
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import mm
import reportlab.lib.enums
import csv
from PIL import Image
from io import BytesIO


def generate_datamatrix(code, size='SquareAuto'):
    encoder = pylibdmtx.encode(code.encode('utf-8'), size=size)
    img = Image.frombytes('RGB', (encoder.width, encoder.height), encoder.pixels)
    return img


def generate_label_full_info(csv_file_path, filename='test_label_bigger.pdf'):
    label_width, label_height = 235, 350
    c = canvas.Canvas(filename, pagesize=(label_width, label_height))
    pdfmetrics.registerFont(TTFont('DejaVuSerif', 'DejaVuSerif.ttf'))
    c.setFont('DejaVuSerif', 12)
    pdfmetrics.registerFont(TTFont('DejaVuSerif-Bold', 'DejaVuSerif-Bold.ttf'))
    styles = getSampleStyleSheet()
    normal_style = styles['BodyText']
    title_style = ParagraphStyle('Title', parent=normal_style, fontName='DejaVuSerif-Bold', fontSize=12)
    dmtx_decoded_str_style = ParagraphStyle('Caption', alignment=reportlab.lib.enums.TA_CENTER,
                                            parent=normal_style, fontName='DejaVuSerif-Bold', fontSize=5, leading=5)
    index_str_style = ParagraphStyle('Index', alignment=reportlab.lib.enums.TA_LEFT,
                                     parent=normal_style, fontName='DejaVuSerif-Bold', fontSize=10)

    datamatrix_multiplier = 0.2  # Adjust this value to change the size of the data matrix
    datamatrix_size = min(label_width, label_height) * datamatrix_multiplier

    with open(csv_file_path) as csvfile:
        reader = csv.reader(csvfile, delimiter='|')
        data = list(reader)

    index = 1

    for entry in data:
        # TODO: define parametres to take as user input
        code, name, size, unit_type, sex, madeof, color, model, country, tp_ts = entry
        img = generate_datamatrix(code)
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)

        f_image = Frame(label_width - (datamatrix_size + 10), label_height - (datamatrix_size + 1),
                        (datamatrix_size + 10), (datamatrix_size + 1), leftPadding=0, bottomPadding=0, rightPadding=0,
                        topPadding=1, id=None, showBoundary=0)
        f_image.addFromList(
            [reportlab.platypus.Image(img_bytes, width=datamatrix_size, height=datamatrix_size), ], c)

        f = Frame(0, label_height - (datamatrix_size + 15),
                  label_width - (datamatrix_size + 10), (datamatrix_size + 15), id=None, showBoundary=0)
        f.addFromList([Paragraph(f'{name}', title_style), ], c)

        f_caption = Frame(label_width - (datamatrix_size + 10), label_height - (datamatrix_size + 15),
                          (datamatrix_size + 10), 14, leftPadding=0, bottomPadding=0, rightPadding=0,
                          topPadding=0, id=None, showBoundary=0)
        # TODO: reportlab paraparser.py works fine? check escape with symbols like '<'
        f_caption.addFromList([Paragraph(
            code[:30].replace('<', '< '), dmtx_decoded_str_style), ], c)

        c.line(0, label_height - (datamatrix_size + 17), label_width, label_height - (datamatrix_size + 17))

        f_table = Frame(0, 0, label_width, label_height - (datamatrix_size + 18), leftPadding=0,
                        bottomPadding=0, rightPadding=0, topPadding=0, id=None, showBoundary=0)
        table_data = [['Размер', size],
                      ['Вид изделия', unit_type],
                      ['Целевой пол', sex],
                      ['Состав', madeof],
                      ['Цвет', color],
                      ['Модель', model],
                      ['Страна', country],
                      ['ТР ТС', tp_ts], ]
        tbl = reportlab.platypus.Table(data=table_data, colWidths=110, rowHeights=30)
        tbl.setStyle(reportlab.platypus.TableStyle([('ALIGN', (0, 0), (0, -1), 'LEFT'),
                                                    ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                                                    ('FONT', (0, 0), (0, -1), 'DejaVuSerif-Bold'),
                                                    ('FONT', (1, 0), (1, -1), 'DejaVuSerif'),
                                                    ('LINEBELOW', (0, 0), (-1, -1), 0.1, reportlab.lib.styles.black),

                                                    ]))
        f_table.addFromList([tbl, ], c)

        f_index = Frame(3, 3, 100, 20, leftPadding=0, bottomPadding=0, rightPadding=0,
                        topPadding=3, id=None, showBoundary=0)
        f_index.addFromList([Paragraph(f'#{index}', index_str_style), ], c)

        f_eac_image = Frame(label_width - 45, 3, 40, 30, leftPadding=0,
                            bottomPadding=0, rightPadding=0, topPadding=0, id=None, showBoundary=0)
        f_eac_image.addFromList([reportlab.platypus.Image('data/demo_samples/eac_image.png',
                                                          width=30, height=30)], c)

        c.showPage()
        index += 1

    c.save()


def generate_label_15_20mm(_data='/home/usr/PycharmProjects/matrix_tags/csv_sample_smaller.csv',
                           label_size=20, filename='test_label_smaller.pdf'):
    label_width = label_height = label_size * mm
    c = canvas.Canvas(filename, pagesize=(label_width, label_height))
    datamatrix_size = label_size * mm

    with open(_data) as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            img = generate_datamatrix(row[0].replace('\\x1d', '\x1d'))
            img_bytes = BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            f_image = Frame(0, 0, label_width, label_height, leftPadding=0, bottomPadding=0, rightPadding=0,
                            topPadding=0, showBoundary=1)
            f_image.addFromList(
                [reportlab.platypus.Image(img_bytes, width=datamatrix_size, height=datamatrix_size), ], c)

            c.showPage()
    c.save()


if __name__ == '__main__':
    generate_label_full_info('/home/usr/PycharmProjects/matrix_tags/data/test/joined_170141723.csv')
