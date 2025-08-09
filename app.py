from flask import Flask, render_template, request, redirect, url_for, flash, session
from pocketbase import PocketBase
from pocketbase.client import ClientResponseError
from dotenv import load_dotenv
from datetime import datetime, timedelta

import os

# Load .env variables
load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv('SECRET_KEY')

# Initialize PocketBase client with your server URL from .env
pb = PocketBase(os.getenv('POCKETBASE_URL'))
status_flow = [
    ("Inquiry", "🟡", "bg-yellow-500"),
    ("Quoting", "🟠", "bg-orange-600"),
    ("Quotation Finalized", "🟢", "bg-green-600"),
    ("Payment Received", "🔵", "bg-blue-600"),
    ("In Shipment", "🔄", "bg-indigo-600"),
    ("Arrived KTM", "🛬", "bg-purple-600"),
    ("Delivered", "✅", "bg-teal-600"),
    ("Closed", "🌟", "bg-pink-600"),
]


# Authenticate admin user once here so pb can perform admin tasks
pb.admins.auth_with_password(
    os.getenv('POCKETBASE_ADMIN_EMAIL'),
    os.getenv('POCKETBASE_ADMIN_PASSWORD')
)

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        try:
            # Authenticate user
            auth_data = pb.collection("users").auth_with_password(email, password)
            
            # Store user info in session
            session['user_id'] = auth_data.record.id
            session['user_email'] = auth_data.record.email
            session['user_name'] = auth_data.record.name if hasattr(auth_data.record, 'name') and auth_data.record.name else auth_data.record.email.split('@')[0]
            session['auth_token'] = auth_data.token
            
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash('Invalid credentials', 'error')
            
    return render_template('login.html')

@app.route('/index')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')
@app.route('/')
def home():
    return render_template('welcome.html')


@app.route('/dashboard')
def dashboard():
        return render_template("dashboard.html")

#######################################################

# Staff Management - Start

#######################################################

# View Staff
@app.route('/staff')
def staff():
    try:
        # Fetch all users from PocketBase users collection
        users = pb.collection('users').get_full_list()
    except ClientResponseError as e:
        flash(f"Error fetching users: {e}", 'error')
        users = []

    return render_template('staff.html', users=users)

# Add Staff
@app.route('/add_staff', methods=['GET', 'POST'])
def add_staff():
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            email = request.form.get('email')
            role = request.form.get('role')
            password = request.form.get('password')
            verified = 'verified' in request.form

            # Create new user in PocketBase
            user_data = {
                'Name': name,  # Changed from 'name' to 'Name'
                'email': email,
                'role': role,
                'password': password,
                'passwordConfirm': password,
                'verified': verified,
                'emailVisibility': True  # Added this field
            }

            pb.collection('users').create(user_data)
            flash('Staff member created successfully!', 'success')
            return redirect(url_for('staff'))

        except ClientResponseError as e:
            flash(f'Error creating staff member: {e}', 'error')

    return render_template('add_staff.html')

# Edit Staff
@app.route('/edit_staff/<user_id>', methods=['GET', 'POST'])
def edit_staff(user_id):
    try:
        # Get user data
        user = pb.collection('users').get_one(user_id)

        if request.method == 'POST':
            name = request.form.get('name')
            email = request.form.get('email')
            role = request.form.get('role')
            password = request.form.get('password')
            verified = 'verified' in request.form

            # Prepare update data
            update_data = {
                'Name': name,  # Changed from 'name' to 'Name'
                'email': email,
                'role': role,
                'verified': verified,
                'emailVisibility': True  # Added this field
            }

            # Only update password if provided
            if password:
                update_data['password'] = password
                update_data['passwordConfirm'] = password

            # Update user in PocketBase
            pb.collection('users').update(user_id, update_data)
            flash('Staff member updated successfully!', 'success')
            return redirect(url_for('staff'))

        return render_template('edit_staff.html', user=user)

    except ClientResponseError as e:
        flash(f'Error: {e}', 'error')
        return redirect(url_for('staff'))


#######################################################

# Staff Management - End

#######################################################




@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        
        try:
            # Request password reset from PocketBase
            pb.collection('users').request_password_reset(email)
            flash('Password reset email sent! Please check your inbox.', 'success')
            return redirect(url_for('login'))
        except ClientResponseError as e:
            if e.status == 404:
                flash('No account found with that email address.', 'error')
            else:
                flash('Error sending password reset email. Please try again.', 'error')
    
    return render_template('forgot_password.html')



@app.route('/reminders')
def reminders():
    return render_template('reminders.html')

@app.route('/suppliers')
def suppliers():
    return render_template('suppliers.html')

@app.route('/add_supplier', methods=['GET', 'POST'])
def add_supplier():
    if request.method == 'POST':
        # handle form data and add to database
        return redirect(url_for('suppliers'))
    return render_template('add_supplier.html')

@app.route('/product')
def product():
    return render_template('product.html')

@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        # handle form data and add to database
        return redirect(url_for('product'))
    return render_template('add_product.html')

@app.route('/customers', methods=['GET', 'POST'])
def customer():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        address = request.form['address']
        notes = request.form['notes']

        try:
            pb.collection('customers').create({
                "name": name,
                "email": email,
                "phone": phone,
                "address": address,
                "notes": notes
            })
            flash('Customer added successfully!', 'success')
        except ClientResponseError as e:
            flash(f"Error adding customer: {e}", 'error')
        return redirect(url_for('customer'))

    try:
        records = pb.collection('customers').get_full_list()
    except ClientResponseError as e:
        flash(f"Error fetching customers: {e}", 'error')
        records = []

    return render_template('customer.html', customers=records)


@app.route('/add_customer', methods=['POST'])
def add_customer():
    name = request.form['name']
    email = request.form['email']
    phone = request.form['phone']
    address = request.form['address']
    notes = request.form['notes']

    try:
        pb.collection('customers').create({
            "name": name,
            "email": email,
            "phone": phone,
            "address": address,
            "notes": notes
        })
        flash('Customer added successfully!', 'success')
    except ClientResponseError as e:
        flash(f"Error adding customer: {e}", 'error')

    return redirect(url_for('customer'))

@app.template_filter('datetimeformat')
def datetimeformat(value):
    from datetime import datetime
    if isinstance(value, datetime):
        return value.strftime("%b %d, %Y")
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S.%f").strftime("%b %d, %Y")

@app.route("/inquiries", methods=["GET", "POST"])
def inquiries():
    if request.method == "POST":
        inquiry_id = request.form.get("inquiry_id")
        new_status = request.form.get("status")
        if inquiry_id and new_status:
            try:
                pb.collection("inquiries").update(inquiry_id, {
                    "status": new_status,
                    "updated": datetime.utcnow().isoformat()
                })
                flash("Inquiry updated successfully!", "success")
            except ClientResponseError as e:
                flash(f"Failed to update inquiry: {e}", "error")
        return redirect(url_for("inquiries"))

    try:
        # Fetch all inquiries (unsorted)
        inquiries = pb.collection("inquiries").get_full_list()
        
        # Sort inquiries by 'updated' field descending in Python
        inquiries.sort(key=lambda i: i.updated, reverse=True)

        customers = {c.id: c for c in pb.collection("customers").get_full_list()}
        products = {p.id: p for p in pb.collection("products").get_full_list()}

        for inquiry in inquiries:
            inquiry.customer_obj = customers.get(inquiry.customer)
            if inquiry.product_ids:
                inquiry.product_objs = [products.get(pid) for pid in inquiry.product_ids.split(",") if pid]
            else:
                inquiry.product_objs = []

    except ClientResponseError as e:
        flash(f"Error fetching inquiries: {e}", "error")
        inquiries = []

    return render_template("inquiries.html", inquiries=inquiries, status_flow=status_flow)


@app.route("/add_inquiry", methods=["GET", "POST"])
def add_inquiry():
    customers = pb.collection("Customers").get_full_list()
    products = pb.collection("Suppliers").get_full_list()

    if request.method == "POST":
        customer_id = request.form.get("Customer")
        selected_products = request.form.getlist("products")

        if not customer_id or not selected_products:
            flash("Customer and at least one product must be selected.", "error")
            return redirect(url_for("add_inquiry"))

        product_ids_str = ",".join(selected_products)

        try:
            pb.collection("inquiries").create({
                "customer": customer_id,
                "product_ids": product_ids_str,
                "status": "Inquiry",
                "updated": datetime.utcnow().isoformat()
            })
            flash("Inquiry created successfully!", "success")
            return redirect(url_for("inquiries"))
        except ClientResponseError as e:
            flash(f"Error creating inquiry: {e}", "error")
            return redirect(url_for("add_inquiry"))

    return render_template("add_inquiry.html", customers=customers, products=products)


@app.route("/inquiry/<inquiry_id>")
def inquiry_detail(inquiry_id):
    inquiry = pb.collection("inquiries").get_one(inquiry_id)
    if not inquiry:
        flash("Inquiry not found.", "error")
        return redirect(url_for("inquiries"))

    customer = pb.collection("Customers").get_one(inquiry.customer)
    products = []
    if inquiry.product_ids:
        product_ids = inquiry.product_ids.split(",")
        products = [pb.collection("products").get_one(pid) for pid in product_ids]

    return render_template("inquiry_detail.html", inquiry=inquiry, customer=customer, products=products, status_flow=status_flow)


@app.route("/update_status/<inquiry_id>", methods=["POST"])
def update_status(inquiry_id):
    new_status = request.form.get("status")
    if new_status not in [s[0] for s in status_flow]:
        flash("Invalid status.", "error")
        return redirect(url_for("inquiry_detail", inquiry_id=inquiry_id))

    # Update status and timestamp
    pb.collection("inquiries").update(inquiry_id, {
        "status": new_status,
        "updated": datetime.utcnow().isoformat()
    })

    flash(f"Status updated to {new_status}", "success")
    return redirect(url_for("inquiry_detail", inquiry_id=inquiry_id))


@app.route('/logout', methods=['POST'])

@app.route('/logout')

def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5050, debug=True)

