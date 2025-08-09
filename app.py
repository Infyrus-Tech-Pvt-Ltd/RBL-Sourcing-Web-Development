from flask import Flask, render_template, request, redirect, url_for, flash, session,jsonify
from pocketbase import PocketBase
from pocketbase.client import ClientResponseError
from dotenv import load_dotenv
from datetime import datetime, timedelta
import requests
import os

# Load .env variables
load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv('SECRET_KEY')


POCKETBASE_URL = os.getenv('POCKETBASE_URL')
COLLECTION = "products"
CUSTOMER_COLLECTION="Customers"
INQUIRY_COLLECTION = "inquiries"

pb = PocketBase(POCKETBASE_URL)

# Authenticate admin and get token for API requests
admin_auth = pb.admins.auth_with_password(
    os.getenv('POCKETBASE_ADMIN_EMAIL'),
    os.getenv('POCKETBASE_ADMIN_PASSWORD')
)
token = admin_auth.token

HEADERS = {
    "Authorization": f"Bearer {token}"
}
status_order = [
    ("Inquiry", "🟡", "bg-yellow-500"),
    ("Quoting", "🟠", "bg-orange-600"),
    ("Quotation Finalized", "🟢", "bg-green-600"),
    ("Payment Received", "🔵", "bg-blue-600"),
    ("In Shipment", "🔄", "bg-indigo-600"),
    ("Arrived KTM", "🛬", "bg-purple-600"),
    ("Delivered", "✅", "bg-teal-600"),
    ("Closed", "🌟", "bg-pink-600"),
]


def generate_next_product_id():
    res = requests.get(f"{POCKETBASE_URL}/api/collections/{COLLECTION}/records", headers=HEADERS, params={"perPage": 100})
    res.raise_for_status()
    products = res.json().get("items", [])

    max_num = 0
    prefix = f"PROD_{os.getenv('CURRENT_YEAR', '2025')}_"
    for p in products:
        pid = p.get("product_id", "")
        if pid.startswith(prefix):
            try:
                num = int(pid[len(prefix):])
                if num > max_num:
                    max_num = num
            except:
                continue
    next_num = max_num + 1
    return f"{prefix}{str(next_num).zfill(4)}"

def generate_next_customer_id():
    res = requests.get(f"{POCKETBASE_URL}/api/collections/{CUSTOMER_COLLECTION}/records", headers=HEADERS, params={"perPage": 100})
    res.raise_for_status()
    products = res.json().get("items", [])

    max_num = 0
    prefix = f"CUST_{os.getenv('CURRENT_YEAR', '2025')}_"
    for p in products:
        pid = p.get("customer_id", "")
        if pid.startswith(prefix):
            try:
                num = int(pid[len(prefix):])
                if num > max_num:
                    max_num = num
            except:
                continue
    next_num = max_num + 1
    return f"{prefix}{str(next_num).zfill(4)}"


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


# product
@app.route('/product')
def product_list():
    res = requests.get(f"{POCKETBASE_URL}/api/collections/{COLLECTION}/records", headers=HEADERS, params={"perPage": 100})
    res.raise_for_status()
    products = res.json().get("items", [])
    products_simple = [
        {
            "id": p["id"],
            "product_id": p.get("product_id", ""),
            "name": p.get("name", ""),
            "supplier": p.get("supplier", ""),
            "model": p.get("model", ""),
            "price": p.get("price", "")
        } for p in products
    ]
    return render_template("product_list.html", products=products_simple)

@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    product_id = request.args.get('id')

    if request.method == 'POST':
        data = request.form.to_dict()
        files = request.files.getlist('uploaded_docs')

        try:
            price = float(data.get("price", 0))
        except ValueError:
            return "Invalid price", 400

        pb_data = {
            "product_id": data.get("product_id"),
            "name": data.get("name"),
            "description": data.get("description"),
            "gross_weight": float(data.get("gross_weight", 0)) if data.get("gross_weight") else None,
            "product_size": data.get("product_size"),
            "hs_code": data.get("hs_code"),
            "tax_rate": float(data.get("tax_rate", 0)) if data.get("tax_rate") else None,
            "vat": float(data.get("vat", 0)) if data.get("vat") else None,
            "qty_per_box": int(data.get("qty_per_box", 0)) if data.get("qty_per_box") else None,
            "box_size": data.get("box_size"),
            "box_weight": float(data.get("box_weight", 0)) if data.get("box_weight") else None,
            "buying_rate": float(data.get("buying_rate", 0)) if data.get("buying_rate") else None,
            "selling_rate": float(data.get("selling_rate", 0)) if data.get("selling_rate") else None,
            "terms": data.get("terms"),
            "specifications": data.get("specifications"),
            "supplier": data.get("supplier"),
            "model": data.get("model"),
            "price": price,
        }

        files_payload = []
        for f in files:
            if f.filename != '':
                files_payload.append(('uploaded_docs', (f.filename, f.stream, f.mimetype)))

        if product_id:
            pb_url = f"{POCKETBASE_URL}/api/collections/{COLLECTION}/records/{product_id}"
            resp = requests.patch(pb_url, data=pb_data, files=files_payload, headers=HEADERS)
        else:
            pb_data["product_id"] = generate_next_product_id()
            pb_url = f"{POCKETBASE_URL}/api/collections/{COLLECTION}/records"
            resp = requests.post(pb_url, data=pb_data, files=files_payload, headers=HEADERS)

        if resp.status_code in (200, 201):
            return redirect(url_for("product_list"))
        else:
            return f"Error saving product: {resp.text}", resp.status_code

    if product_id:
        pb_url = f"{POCKETBASE_URL}/api/collections/{COLLECTION}/records/{product_id}"
        resp = requests.get(pb_url, headers=HEADERS)
        product = resp.json() if resp.status_code == 200 else None
    else:
        product = None

    return render_template("add_product.html", product=product)


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


@app.route('/customers', methods=['GET', 'POST'])
def customers():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        address = request.form['address']
        notes = request.form['notes']
        customer_id = generate_next_customer_id()

        try:
            pb.collection(CUSTOMER_COLLECTION).create({
                "customer_id": customer_id,
                "name": name,
                "email": email,
                "phone": phone,
                "address": address,
                "notes": notes
            })
            flash('Customer added successfully!', 'success')
        except ClientResponseError as e:
            flash(f"Error adding customer: {e}", 'error')
        return redirect(url_for('customers'))

    try:
        records = pb.collection(CUSTOMER_COLLECTION).get_full_list()
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
    customer_id = generate_next_customer_id()

    try:
        pb.collection('Customers').create({  # use correct case
            "customer_id": customer_id,
            "name": name,
            "email": email,
            "phone": phone,
            "address": address,
            "notes": notes
        })
        flash('Customer added successfully!', 'success')
    except ClientResponseError as e:
        flash(f"Error adding customer: {e}", 'error')

    return redirect(url_for('customers'))

@app.template_filter('datetimeformat')
def datetimeformat(value):
    from datetime import datetime
    if isinstance(value, datetime):
        return value.strftime("%b %d, %Y")
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S.%f").strftime("%b %d, %Y")


@app.route("/api/inquiries", methods=["POST"])
def create_inquiry():
    data = request.get_json()
    try:
        customer = pb.collection(CUSTOMER_COLLECTION).get_one(data["customer_id"])
        product = pb.collection(COLLECTION).get_one(data["product_id"])
    except ClientResponseError:
        return jsonify({"error": "Invalid customer or product ID"}), 400

    inquiry_number = f"{customer.customer_id}_{product.product_id}"
    try:
        new_inq = pb.collection(INQUIRY_COLLECTION).create({
            "inquiry_number": inquiry_number,
            "customer_id": data["customer_id"],
            "customer_name": customer.name,
            "product_id": data["product_id"],
            "product_name": product.name,
            "quantity": int(data.get("quantity", 0)),
            "terms": data.get("terms", ""),
            "status": "Inquiry"
        })
        return jsonify(new_inq.to_dict()), 201
    except ClientResponseError as e:
        return jsonify({"error": str(e)}), 400

# Get all inquiries
@app.route("/api/inquiries", methods=["GET"])
def get_inquiries():
    inquiries = pb.collection(INQUIRY_COLLECTION).get_full_list(sort="-created")
    return jsonify([inq.to_dict() for inq in inquiries])

# Customer purchase history
@app.route("/api/customer/<customer_id>/purchases", methods=["GET"])
def get_customer_purchases(customer_id):
    inquiries = pb.collection(INQUIRY_COLLECTION).get_list(
        1, 50, {"filter": f"customer_id='{customer_id}'", "sort": "-created"}
    )
    return jsonify([inq.to_dict() for inq in inquiries.items])

# Delete inquiry
@app.route("/api/inquiries/<inq_id>", methods=["DELETE"])
def delete_inquiry(inq_id):
    try:
        pb.collection(INQUIRY_COLLECTION).delete(inq_id)
        return jsonify({"success": True})
    except ClientResponseError as e:
        return jsonify({"error": str(e)}), 400

# Inquiries page
@app.route("/inquiries")
def inquiries_page():
    customers = pb.collection(CUSTOMER_COLLECTION).get_full_list()
    products = pb.collection(COLLECTION).get_full_list()
    return render_template("inquiries.html", customers=customers, products=products)


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host="127.0.0.1", port=5050, debug=True)

