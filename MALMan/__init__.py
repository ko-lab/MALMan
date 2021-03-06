"""MALMan stands for Members, Accounting and Library Managment

This file will initialize, configure and run the application.
"""

import os
from flask import Flask

app = Flask(__name__)

# set default config values
app.config.update(
    MAX_CONTENT_LENGTH=10 * 1024 * 1024,  # limit requests to 10MiB
    UPLOAD_FOLDER='/uploads',
    UPLOADED_ATTACHMENTS_URL='accounting/attachments/',
    UPLOADED_ATTACHMENTS_ALLOW=['txt', 'rtf', 'odf', 'ods', 'gnumeric', 'abw', 'doc', 'docx',
                                'xls', 'xlsx', 'jpg', 'jpe', 'jpeg', 'png', 'gif', 'svg',
                                'bmp', 'pdf', 'TXT', 'RTF', 'ODF', 'ODS', 'GNUMERIC', 'ABW',
                                'DOC', 'DOCX', 'XLS', 'XLSX', 'JPG', 'JPE', 'JPEG', 'PNG',
                                'GIF', 'SVG', 'BMP', 'PDF'],
    UPLOADED_ATTACHMENTS_DEST=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'attachments'),
    CHANGE_MSG='These values were updated: ',
    ITEMS_PER_PAGE=1000
)

# set config values from config file (and overwrite defaults)
app.config.from_pyfile('MALMan.cfg')

CSRF_ENABLED = True

from MALMan import logs

from MALMan import security

from MALMan import api

from MALMan import views_my_account, views_members, views_bar, views_accounting, views_errors
