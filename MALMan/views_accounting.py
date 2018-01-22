from MALMan import app
import MALMan.database as DB
import MALMan.forms as forms
from MALMan.view_utils import (add_confirmation, return_flash, accounting_categories, permission_required,
                               membership_required, Pagination, upload_attachments, string_to_date)

from flask import render_template, request, redirect, flash, abort, url_for, send_file
from flask.ext.login import current_user
from flask.ext.uploads import UploadSet, configure_uploads
from datetime import date, timedelta

attachments = UploadSet(name='attachments')
configure_uploads(app, attachments)


@app.route("/accounting")
@membership_required()
def accounting():
    banks = DB.Bank.query.all()
    running_account = DB.CashTransaction.query.all()
    running_acount_balance = sum(transaction.amount for transaction in running_account)
    return render_template('accounting/balance.html', banks=banks, running_acount_balance=running_acount_balance)


@app.route("/accounting/log", defaults={'page': 1}, methods=['GET', 'POST'])
@app.route('/accounting/log/page/<int:page>', methods=['GET', 'POST'])
@membership_required()
def accounting_log(page):
    log = DB.Transaction.query.filter(DB.Transaction.date_filed != None).order_by(DB.Transaction.date.desc(), DB.Transaction.bank_statement_number.desc())
    banks = DB.Bank.query.order_by(DB.Bank.id).all()

    form = forms.FilterTransaction()
    form.bank_id.choices = [("", "filter by bank")]
    form.bank_id.choices.extend([(str(bank.id), bank.name) for bank in banks])
    form.category_id.choices = [("", "filter by category")]
    form.category_id.choices.extend(accounting_categories())

    for item in ['is_revenue', 'bank_id', 'category_id']:
        field = request.args.get(item)
        if field:
            setattr(form[item], 'data', field)
            log = log.filter(getattr(DB.Transaction, item) == field)

    item_count = len(log.all())
    log = log.paginate(page, app.config['ITEMS_PER_PAGE'], False).items
    if not log and page != 1:
        abort(404)
    pagination = Pagination(page, app.config['ITEMS_PER_PAGE'], item_count)

    if form.validate_on_submit():
        args = request.view_args.copy()
        for field in ["is_revenue", "bank_id", "category_id"]:
            if request.form[field] != '':
                args[field] = request.form[field]
        return redirect(url_for('accounting_log', **args))
    return render_template('accounting/log.html', log=log, form=form, pagination=pagination)


@app.route("/accounting/accounting/remove_attachment_<transaction_id>_<attachment_id>", methods=['GET', 'POST'])
@permission_required('finances')
def accounting_remove_attachment(transaction_id, attachment_id):
    if 'cancel' in request.form:
        flash("removing the attachment was canceled", "confirmation")
        return redirect(url_for('accounting_log'))

    transaction = DB.Transaction.query.get(transaction_id)
    form = forms.Remove_Attachment()

    if form.validate_on_submit():
        new_attachments = []
        for attachment in transaction.attachments:
            if str(attachment.id) != str(attachment_id):
                new_attachments.append(attachment)
        setattr(transaction, 'attachments', new_attachments)
        DB.db.session.commit()
        flash("the attachment was removed", "confirmation")
        return redirect(url_for('accounting_edit_transaction', transaction_id=transaction.id))

    return render_template('accounting/remove_attachment.html', form=form)


@app.route("/accounting/cashlog", defaults={'page': 1})
@app.route('/accounting/cashlog/page/<int:page>')
@permission_required('finances')
def accounting_cashlog(page):
    log = DB.CashTransaction.query.order_by(DB.CashTransaction.id.desc())

    item_count = len(log.all())
    log = log.paginate(page, app.config['ITEMS_PER_PAGE'], False).items
    if not log and page != 1:
        abort(404)
    pagination = Pagination(page, app.config['ITEMS_PER_PAGE'], item_count)

    return render_template('accounting/cashlog.html', log=log, pagination=pagination)


@app.route("/accounting/request_reimbursement", methods=['GET', 'POST'])
@membership_required()
def accounting_request_reimbursement():
    form = forms.RequestReimbursement()

    if form.validate_on_submit():
        transaction = DB.Transaction(advance_date=string_to_date(request.form["advance_date"]),
                                     is_revenue=False,
                                     amount=request.form["amount"],
                                     description=request.form["description"],
                                     reimbursement_comments=request.form["comments"],
                                     to_from=current_user.name)
        DB.db.session.add(transaction)
        DB.db.session.commit()

        upload_attachments(request, attachments, transaction, DB)

        flash("the request for reimbursement was filed", "confirmation")
        return redirect(request.url)
    return render_template('accounting/request_reimbursement.html', form=form)


@app.route('/accounting/attachments/<filename>')
@membership_required()
def accounting_attachment(filename):
    url = app.config['UPLOADED_ATTACHMENTS_DEST'] + '/' + filename
    return send_file(url, filename)


@app.route("/accounting/approve_reimbursements")
@permission_required('finances')
def accounting_approve_reimbursements():
    requests = DB.Transaction.query.filter_by(date_filed=None)
    return render_template('accounting/list_reimbursements.html', requests=requests)


@app.route("/accounting/approve_<int:transaction_id>", methods=['GET', 'POST'])
@permission_required('finances')
def accounting_approve_reimbursement(transaction_id):
    banks = DB.Bank.query.order_by(DB.Bank.id).all()
    transaction = DB.Transaction.query.get(transaction_id)
    form = forms.ApproveReimbursement(obj=transaction)
    form.bank_id.choices = [(bank.id, bank.name) for bank in banks]
    form.category_id.choices = accounting_categories(IN=False)
    del form.is_revenue
    if form.validate_on_submit():
        transaction.date = string_to_date(request.form["date"])
        transaction.facturation_date = string_to_date(request.form["date"])
        transaction.amount = request.form["amount"]
        transaction.to_from = request.form["to_from"]
        transaction.description = request.form["description"]
        transaction.category_id = request.form["category_id"]
        transaction.bank_id = request.form["bank_id"]
        transaction.bank_statement_number = request.form["bank_statement_number"]
        transaction.date_filed = date.today()
        transaction.filed_by_id = current_user.id
        DB.db.session.commit()

        upload_attachments(request, attachments, transaction, DB)

        flash("the transaction was filed", "confirmation")
        return redirect(url_for('accounting_approve_reimbursements'))
    return render_template('accounting/approve_reimbursement.html', form=form, transaction=transaction)


@app.route("/accounting/add_transaction", methods=['GET', 'POST'])
@permission_required('finances')
def accounting_add_transaction():
    banks = DB.Bank.query.order_by(DB.Bank.id).all()
    form = forms.AddTransaction()
    form.bank_id.choices = [(bank.id, bank.name) for bank in banks]
    form.category_id.choices = accounting_categories()
    if form.validate_on_submit():
        if request.form["facturation_date"] != '':
            facturation_date = string_to_date(request.form["facturation_date"])
        else:
            facturation_date = string_to_date(request.form["date"])
        # convert empty string to None if necessary to prevent a crash
        if request.form["bank_statement_number"] == '':
            bank_statement_number = None
        else:
            bank_statement_number = request.form["bank_statement_number"]
        transaction = DB.Transaction(date=string_to_date(request.form["date"]),
                                     facturation_date=facturation_date,
                                     is_revenue=request.form["is_revenue"],
                                     amount=request.form["amount"],
                                     to_from=request.form["to_from"],
                                     description=request.form["description"],
                                     category_id=request.form["category_id"],
                                     bank_id=request.form["bank_id"],
                                     bank_statement_number=bank_statement_number,
                                     date_filed=date.today(),
                                     filed_by_id=current_user.id)
        DB.db.session.add(transaction)
        DB.db.session.commit()

        upload_attachments(request, attachments, transaction, DB)

        if request.form["category_id"] == '6':
            id = DB.Transaction.query.order_by(DB.Transaction.id.desc()).first()
            return redirect(url_for('topup_bar_account', transaction_id=id.id))
        elif request.form["category_id"] == '8':
            id = DB.Transaction.query.order_by(DB.Transaction.id.desc()).first()
            return redirect(url_for('file_membershipfee', transaction_id=id.id))
        return redirect(url_for('accounting_log'))

        flash("the transaction was filed", "confirmation")
    return render_template('accounting/add_transaction.html', form=form)


@app.route("/accounting/topup_bar_account_<int:transaction_id>", methods=['GET', 'POST'])
@permission_required('finances')
def topup_bar_account(transaction_id):
    users = DB.User.query
    form = forms.TopUpBarAccount()
    form.user_id.choices = [(user.id, user.name) for user in users.order_by('name').all()]
    transaction = DB.Transaction.query.get(transaction_id)
    if form.validate_on_submit():
        item = DB.BarAccountLog(user_id=request.form["user_id"],
                                transaction_id=transaction_id)
        DB.db.session.add(item)
        DB.db.session.commit()
        user = users.get(request.form["user_id"])
        flash(u"\u20AC" + str(transaction.amount) + " was added to " + user.name + "'s bar account", "confirmation")
        return redirect(url_for('accounting_log'))
    return render_template('accounting/topup_bar_account.html', form=form, transaction=transaction)


@app.route("/accounting/edit_<int:transaction_id>", methods=['GET', 'POST'])
@permission_required('finances')
def accounting_edit_transaction(transaction_id):
    banks = DB.Bank.query.all()
    transaction = DB.Transaction.query.get(transaction_id)
    form = forms.EditTransaction(obj=transaction)
    form.bank_id.choices = [(bank.id, bank.name) for bank in banks]
    form.category_id.choices = accounting_categories()
    if form.validate_on_submit():
        confirmation = app.config['CHANGE_MSG']
        atributes = ['date', 'facturation_date', 'is_revenue', 'amount', 'to_from', 'description',
                     'category_id', 'bank_id', 'bank_statement_number']
        for atribute in atributes:
            old_value = getattr(transaction, str(atribute))
            new_value = request.form.get(atribute)
            if atribute == 'is_revenue':
                if new_value == '1':
                    new_value = True
                elif new_value == '0':
                    new_value = False
            elif atribute in ['date', 'facturation_date']:
                new_value = string_to_date(request.form.get(atribute))
            if str(new_value) != str(old_value):
                if atribute == 'facturation_date' and new_value == '':
                    new_value = request.form.get('date')
                setattr(transaction, atribute, new_value)
                confirmation = add_confirmation(confirmation, str(atribute) + " = " + str(new_value) +
                                                " (was " + str(old_value) + ")")
            transaction.date_filed
        DB.db.session.commit()

        uploadconfirmation = upload_attachments(request, attachments, transaction, DB)

        confirmation = add_confirmation(confirmation, uploadconfirmation)
        return_flash(confirmation)
        return redirect(request.url)
    return render_template('accounting/edit_transaction.html', form=form, transaction=transaction)


@app.route("/accounting/membershipfees", defaults={'page': 1}, methods=['GET', 'POST'])
@app.route('/accounting/membershipfees/page/<int:page>')
@permission_required('finances')
def accounting_membershipfees(page):
    log = DB.MembershipFee.query
    users = DB.User.query

    form = forms.FilterMembershipFees()
    form.user.choices = [("", "filter by user")]
    form.user.choices.extend([(str(user.id), user.name) for user in users.order_by('name')])

    user = request.args.get('user')
    if user:
        log = log.filter_by(user_id=user)
        setattr(form.user, 'data', user)

    item_count = len(log.all())
    log = log.paginate(page, app.config['ITEMS_PER_PAGE'], False).items
    if not log and page != 1:
        abort(404)
    pagination = Pagination(page, app.config['ITEMS_PER_PAGE'], item_count)

    if form.validate_on_submit():
        args = request.view_args.copy()
        if request.form['user'] != '':
            args['user'] = request.form['user']
        return redirect(url_for('accounting_membershipfees', **args))

    return render_template('accounting/membershipfees.html', log=log, pagination=pagination, form=form)


@app.route("/accounting/file_membershipfee_<int:transaction_id>", methods=['GET', 'POST'])
@permission_required('finances')
def file_membershipfee(transaction_id):
    users = DB.User.query
    form = forms.FileMembershipFee()
    form.user_id.choices = [(user.id, user.name) for user in users.order_by('name').all()]
    transaction = DB.Transaction.query.get(transaction_id)

    if form.validate_on_submit():
        payeduntil = string_to_date(request.form["until"])
        payeduntil = payeduntil.replace(month=payeduntil.month+1, day=1) - timedelta(days=1)
        item = DB.MembershipFee(user_id=request.form["user_id"],
                                transaction_id=transaction_id,
                                until=payeduntil)
        DB.db.session.add(item)
        DB.db.session.commit()
        user = users.get(request.form["user_id"])
        flash(user.name + "'s membership dues are paid until then end of " + payeduntil.strftime('%Y-%m'), "confirmation")
        return redirect(url_for('accounting_log'))

    return render_template('accounting/file_membershipfee.html', form=form, transaction=transaction)


@app.route("/accounting/kasboek", methods=['GET', 'POST'])
@membership_required()
def accounting_kasboek():
    log = DB.Transaction.query.filter(DB.Transaction.facturation_date != None).order_by(DB.Transaction.facturation_date.asc())
    banks = DB.Bank.query.order_by(DB.Bank.id).all()
    years = [transaction.facturation_date.year for transaction in log]
    years = list(set(years))  # remove duplicates
    years = sorted(years, reverse=True)

    form = forms.FilterKasboek()

    form.bank.choices = [(bank.name, bank.name) for bank in banks]
    form.year.choices = [(year, year) for year in years]

    # filter by bank and year
    bank_name = request.args.get('bank') or banks[0].name
    log = log.filter(DB.Transaction.bank.has(name=bank_name)).all()
    form.bank.data = bank_name
    if years:
        year = int(request.args.get('year') or years[0])
        log = [transaction for transaction in log if transaction.date.year == year]
        form.year.data = year

    if form.validate_on_submit():
        args = request.view_args.copy()
        args['bank'] = request.form['bank']
        args['year'] = request.form['year']
        return redirect(url_for('accounting_kasboek', **args))

    return render_template('accounting/kasboek.html', log=log, banks=banks, form=form)


@app.route("/accounting/dagboek", methods=['GET', 'POST'])
@membership_required()
def accounting_dagboek():
    log = DB.Transaction.query.filter(DB.Transaction.facturation_date != None).order_by(DB.Transaction.facturation_date.asc())
    banks = DB.Bank.query.order_by(DB.Bank.id).all()
    years = [transaction.facturation_date.year for transaction in log]
    years = list(set(years))  # remove duplicates
    years = sorted(years, reverse=True)

    form = forms.FilterDagboek()
    form.year.choices = [(year, year) for year in years]

    # filter by type
    type = request.args.get('type') or "revenues"
    if type == "revenues":
        is_revenue = True
    else:
        is_revenue = False
    form.is_revenue.data = type
    # we don't remove transactions yet because we need all of them for the count below

    # filter by year
    if years:
        year = int(request.args.get('year') or years[0])
        log = [transaction for transaction in log if transaction.facturation_date.year == year]
        form.year.data = year

    # We build the list over here instead of in the template because the numbering is too complex
    transactions = []
    used_banks = []
    used_categories = []
    for entry in log:
        transaction = {}
        transaction['id'] = entry.id
        transaction['facturation_date'] = entry.facturation_date
        transaction['description'] = entry.description
        transaction['amount'] = entry.amount
        for bank in banks:
            if entry.bank_id == bank.id:
                # get the transactions with the same bank, sort them by
                # facturation date and find out how many transactions precede
                # the current transaction
                transactions_same_bank = [item for item in log if item.bank_id == bank.id]
                transactions_same_bank.sort(key=lambda k: k.facturation_date)
                for position, item in enumerate(transactions_same_bank):
                    if item.id == entry.id:
                        count = position + 1
                transaction['number_' + str(bank.name)] = count
                transaction['bank_' + str(bank.name)] = entry.amount
                used_banks.append(bank.name)
        transaction['category_' + entry.category.legal_category] = entry.amount
        if entry.is_revenue == is_revenue:
            transactions.append(transaction)
            used_categories.append(entry.category.legal_category)
    used_banks = set(used_banks)
    used_categories = list(set(used_categories))
    used_categories.sort()

    if form.validate_on_submit():
        args = request.view_args.copy()
        args['type'] = request.form['is_revenue']
        args['year'] = request.form['year']
        return redirect(url_for('accounting_dagboek', **args))

    return render_template('accounting/dagboek.html', transactions=transactions,
                           form=form, banks=used_banks, categories=used_categories)
