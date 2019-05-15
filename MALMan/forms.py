"""Define the various forms used in MALMan"""

from flask_security.forms import ConfirmRegisterForm, unique_user_email
from flask_uploads import UploadSet, configure_uploads
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import validators, ValidationError
from wtforms.fields import StringField, BooleanField, PasswordField, DateField, IntegerField, SubmitField, SelectField, \
    DecimalField, TextAreaField

import MALMan.database as DB
from MALMan import app

attachments = UploadSet(name='attachments')
configure_uploads(app, attachments)


def check_category(form, field):
    """Checks if the category type matches the is_revenue field"""
    is_revenue = form['is_revenue'].data
    categories = DB.AccountingCategory.query.all()
    revenue_categories = [str(category.id) for category in categories if category.is_revenue]
    if field.data in revenue_categories and not is_revenue:
        raise ValidationError('This is a revenue, please pick a corresponding category')
    if field.data not in revenue_categories and is_revenue:
        raise ValidationError('This is an expense, please pick a corresponding category')


def check_unique_stock_name(form, field):
    """Checks if the stock item's name is unique"""
    exists = DB.StockItem.query.filter_by(name=field.data).all()
    if exists:
        raise ValidationError('There is already a stockitem with this name')


def check_positive_number(form, field):
    """Checks if the number is positive  because in python 3 wtform returns: TypeError: '<' not supported between
    instances of 'str' and 'int' """
    int(field.data)

class NewMembers(FlaskForm):
    # some fields are added by the view
    submit = SubmitField("activate account(s)")


class MembersEditOwnAccount(FlaskForm):
    email = StringField('Email', [
        validators.Email(message='please enter a valid email address')])
    name = StringField('Name', [validators.DataRequired()])
    date_of_birth = DateField('Date of birth (yyyy-mm-dd)',
                              [validators.DataRequired(
                                  message='please enter a date using the specified formatting')])
    street = StringField('Street', [
        validators.DataRequired()])
    number = IntegerField('Number',
                          [check_positive_number])
    bus = StringField('Bus (optional)', [
        validators.Optional()])
    postalcode = StringField('Postal code',
                             [check_positive_number,
                              validators.DataRequired()])
    city = StringField('City', [
        validators.DataRequired()])
    telephone = StringField('Telephone (0xx.xxx.xxx)',
                            [validators.Length(min=8,
                                               message='entry is not long enough to be a valid phone number'),
                             validators.DataRequired()])
    show_email = BooleanField('Display email address to other members')
    show_telephone = BooleanField('Display phone number to other members')
    submit = SubmitField("edit my account information")


class MembersEditAccount(MembersEditOwnAccount):
    # some fields are added by the view
    membership_dues = DecimalField('Monthly dues (&euro;)', [
        validators.NumberRange(min=0,
                               message='please enter a positive number')])
    submit = SubmitField("edit account information")


class MembersEditPassword(FlaskForm):
    password = PasswordField("Password", [
        validators.Length(
            message="Password must be at least 6 characters long", min=6)])
    password_confirm = PasswordField("Retype Password", [
        validators.EqualTo('password', message="Passwords do not match")])
    submit = SubmitField("change my password")


class RegisterForm(MembersEditOwnAccount, ConfirmRegisterForm):
    '''The register form'''
    motivation = TextAreaField('My motivation to become a member:',
                               [validators.DataRequired()])
    email = StringField('Email', [unique_user_email,
                                  validators.Email(message='please enter a valid email address')])
    submit = SubmitField("create my account")

    def to_dict(self):
        return dict(
            email=self.email.data,
            password=self.password.data,
            name=self.name.data,
            street=self.street.data,
            number=self.number.data,
            bus=self.bus.data,
            postalcode=self.postalcode.data,
            city=self.city.data,
            date_of_birth=self.date_of_birth.data,
            telephone=self.telephone.data,
            show_telephone=self.show_telephone.data,
            show_email=self.show_email.data,
            motivation=self.motivation.data)


class MembersRemoveMember(FlaskForm):
    submit = SubmitField('remove member')


class BarRemoveItem(FlaskForm):
    submit = SubmitField('remove stock item')


class BarActivateItem(FlaskForm):
    # some fields are added by the view
    submit = SubmitField("activate stock item(s)")


# this is not used, check views.py for more info
class BarEditAmounts(FlaskForm):
    # some fields are added by the view
    submit = SubmitField('ok!')


class BarEditItem(FlaskForm):
    # some fields are added by the view
    name = StringField('name', [validators.DataRequired()])
    price = DecimalField('price (e.g. 1.52)',
                         [validators.NumberRange(min=0,
                                                 message='please enter a positive number')], places=2)
    stock_max = IntegerField('Maximum stock',
                             [validators.NumberRange(min=0,
                                                     message='please enter a positive number')])
    category_id = SelectField('category', coerce=int)
    josto = BooleanField('josto')


class BarEdit(FlaskForm):
    # the view adds a BarEditItem form for each stock item
    submit = SubmitField('edit stock items')


class StockupJostoFlaskFormMixin(FlaskForm):
    amount = IntegerField([validators.NumberRange(min=0, message='please enter a positive number')])
    check = BooleanField()


class BarAddItem(FlaskForm):
    name = StringField('Name', [validators.DataRequired(), check_unique_stock_name])
    price = DecimalField('Price (e.g. 1.52)',
                         [validators.NumberRange(min=0,
                                                 message='please enter a positive number')],
                         places=2)
    stock_max = IntegerField('Stock maximum',
                             [validators.NumberRange(min=0,
                                                     message='please enter a positive number')])
    category_id = SelectField('Category', coerce=int)
    josto = BooleanField('Josto')
    submit = SubmitField('add stock item')


class AddTransaction(FlaskForm):
    date = DateField('date (yyyy-mm-dd)',
                     [validators.DataRequired(
                         message='please enter a date using the specified formatting')])
    facturation_date = DateField('facturation date (optional, yyyy-mm-dd)',
                                 [validators.Optional()])
    is_revenue = SelectField('type',
                             choices=[(1, "revenue"), (0, "expense")], coerce=int)
    amount = DecimalField('amount (e.g. 1.52)',
                          [validators.NumberRange(message='please enter a positive or negative number')], places=2)
    description = StringField('description', [validators.DataRequired()])
    bank_id = SelectField('bank', coerce=int)
    to_from = StringField('to/from', [validators.DataRequired()])
    category_id = SelectField('category', [check_category])
    bank_statement_number = IntegerField('bank statement number (optional)',
                                         [validators.Optional(), validators.NumberRange(min=0,
                                                                                        message='please enter a positive number')])
    attachment = FileField("add attachment",
                           [FileAllowed(attachments, "This filetype is not whitelisted")])
    submit = SubmitField('file transaction')


class TopUpBarAccount(FlaskForm):
    user_id = SelectField('user', coerce=int)
    submit = SubmitField('top up')


class FileMembershipFee(FlaskForm):
    user_id = SelectField('Member', coerce=int)
    until = DateField("This settles this member's membership dues up until and including (yyyy-mm-dd)",
                      [validators.DataRequired(
                          message='please enter a date using the specified formatting')])
    submit = SubmitField('file payment of membership fee')


class EditTransaction(AddTransaction):
    attachment = FileField("add attachment",
                           [FileAllowed(attachments, "This filetype is not whitelisted")])
    submit = SubmitField('edit transaction')


class RequestReimbursement(FlaskForm):
    advance_date = DateField('date of advance (yyyy-mm-dd)',
                             [validators.DataRequired(
                                 message='please enter a date using the specified formatting')])
    amount = DecimalField('amount advanced (e.g. 1.52)',
                          [validators.NumberRange(min=0, message='please enter a positive number')], places=2)
    description = StringField('description', [validators.DataRequired()])
    comments = StringField('comments (optional, e.g. how you prefer to be reimbursed)', [validators.Optional()])
    attachment = FileField("add attachment",
                           [FileAllowed(attachments, "This filetype is not whitelisted")])
    submit = SubmitField('request reimbursement')


class Remove_Attachment(FlaskForm):
    cancel = SubmitField('cancel')
    submit = SubmitField('remove attachment')


class ApproveReimbursement(AddTransaction):
    category_id = SelectField('category')
    date = DateField('date of reimbursement (yyyy-mm-dd)',
                     [validators.DataRequired(
                         message='please enter a date using the specified formatting')])


class FilterTransaction(FlaskForm):
    is_revenue = SelectField('type',
                             choices=[("", "filter by type"), ("1", "revenues"), ("0", "expenses")])
    category_id = SelectField('category_id')
    bank_id = SelectField('bank')
    submit = SubmitField('filter')


class FilterMembershipFees(FlaskForm):
    user = SelectField('user')
    user.choices = [("0", "filter by user")]
    submit = SubmitField('filter')


class FilterKasboek(FlaskForm):
    year = SelectField('year', coerce=int)
    bank = SelectField('bank')
    submit = SubmitField('go')


class FilterDagboek(FlaskForm):
    year = SelectField('year', coerce=int)
    is_revenue = SelectField('type',
                             choices=[("revenues", "revenues"), ("expenses", "expenses")])
    submit = SubmitField('go')
