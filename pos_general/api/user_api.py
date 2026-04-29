import frappe
import random
from frappe.utils import random_string
from frappe.contacts.doctype.contact.contact import get_contact_name
from frappe.utils.password import update_password as set_new_password

@frappe.whitelist(allow_guest=True)
def register_user(email, phone, first_name, password, last_name=None):
    if not email and not phone:
        return {'status': 'error', 'message': 'Email or phone number is required'}

    if email and frappe.db.exists('User', {'email': email}):
        return {'status': 'error', 'message': 'User with this email already exists'}
    if phone and frappe.db.exists('User', {'phone': phone}):
        return {'status': 'error', 'message': 'User with this phone number already exists'}

    user = frappe.get_doc({
        'doctype': 'User',
        'email': email,
        'phone': phone,
        'first_name': first_name,
        'last_name': last_name,
        'enabled': 1,
        'new_password': password or random_string(10)
    })

    user.insert(ignore_permissions=True)

    role_name = 'Sales User'
    if not frappe.db.exists('Role', {'role_name': role_name}):
        return {'status': 'error', 'message': f'Role {role_name} does not exist'}

    role_assignment = frappe.get_doc({
        'doctype': 'Has Role',
        'parent': user.name,
        'parenttype': 'User',
        'parentfield': 'roles',
        'role': role_name
    })
    role_assignment.insert(ignore_permissions=True)

    user.reload()

    customer = frappe.get_doc({
        'doctype': 'Customer',
        'customer_name': f"{first_name} {last_name}" if last_name else first_name,
        'customer_type': 'Individual',
        'customer_group': 'Individual',
        'territory': 'Pakistan'
    })

    customer.insert(ignore_permissions=True)

    user.customer = customer.name
    user.save(ignore_permissions=True)

    contact = custom_create_contact(user)

   
    if contact:
        customer.customer_primary_contact = contact.name
        customer.save(ignore_permissions=True)

    frappe.db.commit()

    return {'status': 'success', 'message': 'User registered, role assigned, and customer created successfully'}

def custom_create_contact(user, ignore_links=False, ignore_mandatory=False):
    if user.name in ["Administrator", "Guest"]:
        return

    contact_name = get_contact_name(user.email)
    if not contact_name:

        contact = frappe.get_doc({
            "doctype": "Contact",
            "first_name": user.first_name,
            "last_name": user.last_name,
            "user": user.name,
            "gender": user.gender,
            "name": user.first_name
        })

        if user.email:
            contact.add_email(user.email, is_primary=True)

        if user.phone:
            contact.add_phone(user.phone, is_primary_phone=True)

        if user.mobile_no:
            contact.add_phone(user.mobile_no, is_primary_mobile_no=True)

        if user.customer:
            contact.append('links', {
                'link_doctype': 'Customer',
                'link_name': user.customer
            })

        contact.insert(ignore_permissions=True, ignore_links=ignore_links, ignore_mandatory=ignore_mandatory)
        
        return contact 

    else:
        contact = frappe.get_doc("Contact", contact_name)
        return contact
      
@frappe.whitelist(allow_guest=True)
def reset_password(email, new_password):
    user = frappe.db.get_value("User", {"email": email})
    
    if not user:
        return {"status": "Failed", "message": "User not found"}
    
    try:
        user_doc = frappe.get_doc("User", user)

        user_doc.new_password = new_password
        
        user_doc.save(ignore_permissions=True)
        
        frappe.db.commit()

        return {"status": "Success", "message": "Password updated successfully"}
    except Exception as e:
        return {"status": "Failed", "message": str(e)}
    
@frappe.whitelist(allow_guest=True)
def send_otp_via_email(otp, email):
    try:
        if not frappe.db.exists("User", {"email": email}):
            return {"status": 404, "message": "User not found"}
        
        if not otp:
            otp = str(random.randint(100000, 999999))
        
        subject = "Your OTP Code"
        message = f"Dear User,\n\nYour OTP code is: {otp}\n\nThank you!"
        
        try:
            frappe.sendmail(recipients=email, subject=subject, message=message)
            return {"status": 200, "message": "OTP sent successfully"}
        except Exception as e:
            return {"status": 500, "message": f"Failed to send email. Error: {str(e)}"}
    
    except Exception as e:
        return {"status": 500, "message": f"Server error: {str(e)}"}

    
@frappe.whitelist(allow_guest=True)
def check_user_exist(email):
        if not frappe.db.exists("User", {"email": email}):
            return {"status": 404, "message": "User not found"}
        else :
            return {"status": 200, "message": "User found"}
   
    
    