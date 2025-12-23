from flask import Blueprint, request, jsonify
from database import get_db_connection
from datetime import datetime
import secrets
import string

partner_app_bp = Blueprint('partner_applications', __name__)

# Generate random password
def generate_temp_password(length=8):
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))

# Submit new partner application
@partner_app_bp.route('/apply', methods=['POST'])
def submit_application():
    try:
        data = request.get_json()
        
        required_fields = ['manager_name', 'manager_phone', 'restaurant_name', 
                          'restaurant_phone', 'restaurant_email', 'address', 'has_license']
        
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if email already exists
        existing = cursor.execute(
            'SELECT id FROM partner_applications WHERE restaurant_email = ?',
            (data['restaurant_email'],)
        ).fetchone()
        
        if existing:
            conn.close()
            return jsonify({'error': 'An application with this email already exists'}), 409
        
        # Insert new application
        cursor.execute('''
            INSERT INTO partner_applications 
            (manager_name, manager_phone, restaurant_name, restaurant_phone, 
             restaurant_email, address, hotline, has_license, status, applied_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
        ''', (
            data['manager_name'],
            data['manager_phone'],
            data['restaurant_name'],
            data['restaurant_phone'],
            data['restaurant_email'],
            data['address'],
            data.get('hotline', 'N/A'),
            data['has_license'],
            datetime.now().isoformat()
        ))
        
        conn.commit()
        application_id = cursor.lastrowid
        conn.close()
        
        return jsonify({
            'message': 'Application submitted successfully',
            'application_id': application_id
        }), 201
        
    except Exception as e:
        print(f"Error in submit_application: {str(e)}")
        return jsonify({'error': str(e)}), 500


# Check application status by email
@partner_app_bp.route('/check-status', methods=['POST'])
def check_application_status():
    try:
        data = request.get_json()
        
        if 'email' not in data:
            return jsonify({'error': 'Email is required'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        application = cursor.execute(
            'SELECT * FROM partner_applications WHERE restaurant_email = ?',
            (data['email'],)
        ).fetchone()
        
        conn.close()
        
        if not application:
            return jsonify({'error': 'No application found with this email'}), 404
        
        app_dict = dict(application)
        
        # Include temp_password only if approved
        if app_dict['status'] != 'approved':
            app_dict.pop('temp_password', None)
        
        return jsonify({
            'status': app_dict['status'],
            'application': app_dict
        }), 200
        
    except Exception as e:
        print(f"Error in check_application_status: {str(e)}")
        return jsonify({'error': str(e)}), 500


# Partner login
@partner_app_bp.route('/login', methods=['POST'])
def partner_login():
    try:
        data = request.get_json()
        
        if 'email' not in data or 'password' not in data:
            return jsonify({'error': 'Email and password are required'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get application with approved status
        application = cursor.execute(
            'SELECT * FROM partner_applications WHERE restaurant_email = ?',
            (data['email'],)
        ).fetchone()
        
        conn.close()
        
        if not application:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        app_dict = dict(application)
        
        # Check if application is approved
        if app_dict['status'] != 'approved':
            return jsonify({'error': 'Application not approved yet'}), 401
        
        # Check if temp_password exists
        if not app_dict.get('temp_password'):
            return jsonify({'error': 'No password set. Please contact admin.'}), 401
        
        # Check password (compare as strings)
        if str(app_dict['temp_password']).strip() != str(data['password']).strip():
            print(f"Password mismatch: DB='{app_dict['temp_password']}' vs Input='{data['password']}'")
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Return restaurant info without sensitive data
        return jsonify({
            'message': 'Login successful',
            'restaurant': {
                'id': app_dict['id'],
                'name': app_dict['restaurant_name'],
                'email': app_dict['restaurant_email'],
                'phone': app_dict['restaurant_phone'],
                'address': app_dict['address'],
                'manager_name': app_dict['manager_name'],
                'hotline': app_dict.get('hotline', 'N/A')
            }
        }), 200
        
    except Exception as e:
        print(f"Error in partner_login: {str(e)}")
        return jsonify({'error': str(e)}), 500


# Get all applications (Admin)
@partner_app_bp.route('/applications', methods=['GET'])
def get_applications():
    try:
        status_filter = request.args.get('status')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if status_filter:
            applications = cursor.execute(
                'SELECT * FROM partner_applications WHERE status = ? ORDER BY applied_at DESC',
                (status_filter,)
            ).fetchall()
        else:
            applications = cursor.execute(
                'SELECT * FROM partner_applications ORDER BY applied_at DESC'
            ).fetchall()
        
        conn.close()
        
        apps_list = [dict(app) for app in applications]
        
        return jsonify({
            'applications': apps_list,
            'total': len(apps_list)
        }), 200
        
    except Exception as e:
        print(f"Error in get_applications: {str(e)}")
        return jsonify({'error': str(e)}), 500


# Update application status (Approve/Reject)
@partner_app_bp.route('/applications/<int:app_id>/status', methods=['PUT'])
def update_application_status(app_id):
    try:
        data = request.get_json()
        
        if 'status' not in data:
            return jsonify({'error': 'Status is required'}), 400
        
        new_status = data['status']
        
        if new_status not in ['pending', 'approved', 'rejected']:
            return jsonify({'error': 'Invalid status'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if application exists
        existing = cursor.execute(
            'SELECT * FROM partner_applications WHERE id = ?',
            (app_id,)
        ).fetchone()
        
        if not existing:
            conn.close()
            return jsonify({'error': 'Application not found'}), 404
        
        # Generate temp password if approving
        temp_password = None
        reviewed_at = datetime.now().isoformat()
        
        if new_status == 'approved':
            temp_password = generate_temp_password()
            print(f"Generated password for app {app_id}: {temp_password}")
            
            cursor.execute('''
                UPDATE partner_applications 
                SET status = ?, reviewed_at = ?, temp_password = ?
                WHERE id = ?
            ''', (new_status, reviewed_at, temp_password, app_id))
        else:
            cursor.execute('''
                UPDATE partner_applications 
                SET status = ?, reviewed_at = ?, temp_password = NULL
                WHERE id = ?
            ''', (new_status, reviewed_at, app_id))
        
        conn.commit()
        
        # Verify the update
        updated = cursor.execute(
            'SELECT * FROM partner_applications WHERE id = ?',
            (app_id,)
        ).fetchone()
        
        conn.close()
        
        response = {
            'message': f'Application {new_status} successfully',
            'application_id': app_id,
            'status': new_status
        }
        
        if temp_password:
            response['temp_password'] = temp_password
            print(f"Approval successful. Email: {dict(updated)['restaurant_email']}, Password: {temp_password}")
        
        return jsonify(response), 200
        
    except Exception as e:
        print(f"Error in update_application_status: {str(e)}")
        return jsonify({'error': str(e)}), 500


# Get statistics
@partner_app_bp.route('/statistics', methods=['GET'])
def get_statistics():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        total = cursor.execute('SELECT COUNT(*) as count FROM partner_applications').fetchone()['count']
        pending = cursor.execute('SELECT COUNT(*) as count FROM partner_applications WHERE status = "pending"').fetchone()['count']
        approved = cursor.execute('SELECT COUNT(*) as count FROM partner_applications WHERE status = "approved"').fetchone()['count']
        rejected = cursor.execute('SELECT COUNT(*) as count FROM partner_applications WHERE status = "rejected"').fetchone()['count']
        
        conn.close()
        
        return jsonify({
            'total': total,
            'pending': pending,
            'approved': approved,
            'rejected': rejected
        }), 200
        
    except Exception as e:
        print(f"Error in get_statistics: {str(e)}")
        return jsonify({'error': str(e)}), 500
    # Update partner application details
@partner_app_bp.route('/applications/<int:app_id>/update', methods=['PUT'])
def update_partner_info(app_id):
    try:
        data = request.get_json()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if application exists
        existing = cursor.execute(
            'SELECT * FROM partner_applications WHERE id = ?',
            (app_id,)
        ).fetchone()
        
        if not existing:
            conn.close()
            return jsonify({'error': 'Application not found'}), 404
        
        # Update the information
        cursor.execute('''
            UPDATE partner_applications 
            SET manager_name = ?, restaurant_phone = ?, hotline = ?, address = ?
            WHERE id = ?
        ''', (
            data['manager_name'],
            data['restaurant_phone'],
            data.get('hotline', 'N/A'),
            data['address'],
            app_id
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Information updated successfully'}), 200
        
    except Exception as e:
        print(f"Error in update_partner_info: {str(e)}")
        return jsonify({'error': str(e)}), 500


# Change partner password
@partner_app_bp.route('/applications/<int:app_id>/change-password', methods=['PUT'])
def change_partner_password(app_id):
    try:
        data = request.get_json()
        
        if 'current_password' not in data or 'new_password' not in data:
            return jsonify({'error': 'Current and new passwords are required'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get application
        application = cursor.execute(
            'SELECT * FROM partner_applications WHERE id = ?',
            (app_id,)
        ).fetchone()
        
        if not application:
            conn.close()
            return jsonify({'error': 'Application not found'}), 404
        
        app_dict = dict(application)
        
        # Verify current password
        if str(app_dict.get('temp_password', '')).strip() != str(data['current_password']).strip():
            conn.close()
            return jsonify({'error': 'Current password is incorrect'}), 401
        
        # Update to new password
        cursor.execute('''
            UPDATE partner_applications 
            SET temp_password = ?
            WHERE id = ?
        ''', (data['new_password'], app_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Password changed successfully'}), 200
        
    except Exception as e:
        print(f"Error in change_partner_password: {str(e)}")
        return jsonify({'error': str(e)}), 500