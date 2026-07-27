import csv
import io
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response, jsonify
from blueprints.auth import login_required
from database import get_db_connection, calculate_pending_days

complaints_bp = Blueprint('complaints', __name__)

WARDS = [f'Ward {i}' for i in range(1, 11)]
FAULT_TYPES = [
    'Bulb Replacement',
    'Wiring Damage',
    'Transformer Failure',
    'Pole Structural Damage',
    'Switch Failure',
    'Power Surge',
    'Solar Panel Breakdown'
]
STATUSES = ['Pending', 'In Progress', 'Repaired', 'Rejected']

def generate_fault_id(conn):
    """Auto-generates sequential Fault ID in format FLT-2026-XXXX"""
    row = conn.execute("SELECT MAX(id) FROM complaints").fetchone()
    next_num = (row[0] or 1000) + 1
    return f"FLT-2026-{next_num}"

@complaints_bp.route('/complaints')
@login_required
def list_complaints():
    search = request.args.get('search', '').strip()
    ward_filter = request.args.get('ward', '').strip()
    fault_filter = request.args.get('fault_type', '').strip()
    status_filter = request.args.get('status', '').strip()
    sort_by = request.args.get('sort', 'reported_date')
    order = request.args.get('order', 'desc')
    page = int(request.args.get('page', 1))
    per_page = 10
    
    conn = get_db_connection()
    
    # Base query
    query = "SELECT * FROM complaints WHERE 1=1"
    params = []
    
    if search:
        query += " AND (fault_id LIKE ? OR pole_id LIKE ? OR street LIKE ? OR ward LIKE ?)"
        pattern = f"%{search}%"
        params.extend([pattern, pattern, pattern, pattern])
        
    if ward_filter:
        query += " AND ward = ?"
        params.append(ward_filter)
        
    if fault_filter:
        query += " AND fault_type = ?"
        params.append(fault_filter)
        
    if status_filter:
        query += " AND status = ?"
        params.append(status_filter)
        
    # Count total matching records for pagination
    count_query = f"SELECT COUNT(*) FROM ({query})"
    total_records = conn.execute(count_query, params).fetchone()[0]
    total_pages = max(1, (total_records + per_page - 1) // per_page)
    
    # Sanitize sort field
    valid_sorts = {
        'fault_id': 'fault_id',
        'pole_id': 'pole_id',
        'ward': 'ward',
        'street': 'street',
        'reported_date': 'reported_date',
        'fault_type': 'fault_type',
        'status': 'status'
    }
    sql_sort = valid_sorts.get(sort_by, 'reported_date')
    sql_order = 'ASC' if order.lower() == 'asc' else 'DESC'
    
    # Fetch paginated rows
    offset = (page - 1) * per_page
    query += f" ORDER BY {sql_sort} {sql_order} LIMIT ? OFFSET ?"
    params.extend([per_page, offset])
    
    rows = conn.execute(query, params).fetchall()
    
    # Calculate derived pending_days for each row
    complaints_list = []
    for r in rows:
        c = dict(r)
        c['pending_days'] = calculate_pending_days(c['reported_date'], c['repaired_date'], c['status'])
        complaints_list.append(c)
        
    conn.close()
    
    return render_template(
        'complaint_list.html',
        complaints=complaints_list,
        wards=WARDS,
        fault_types=FAULT_TYPES,
        statuses=STATUSES,
        search=search,
        selected_ward=ward_filter,
        selected_fault=fault_filter,
        selected_status=status_filter,
        sort_by=sort_by,
        order=order,
        page=page,
        total_pages=total_pages,
        total_records=total_records
    )

@complaints_bp.route('/complaints/register', methods=['GET', 'POST'])
@login_required
def register_complaint():
    conn = get_db_connection()
    auto_fault_id = generate_fault_id(conn)
    
    if request.method == 'POST':
        fault_id = request.form.get('fault_id', auto_fault_id).strip()
        pole_id = request.form.get('pole_id', '').strip()
        ward = request.form.get('ward', '').strip()
        street = request.form.get('street', '').strip()
        reported_date = request.form.get('reported_date', '').strip()
        fault_type = request.form.get('fault_type', '').strip()
        status = request.form.get('status', 'Pending').strip()
        repaired_date = request.form.get('repaired_date', '').strip() or None
        
        # Server-side Validation
        errors = []
        if not pole_id:
            errors.append("Pole ID is required (e.g. POL-101).")
        if not ward:
            errors.append("Ward selection is required.")
        if not street:
            errors.append("Street name is required.")
        if not reported_date:
            errors.append("Reported date is required.")
        if not fault_type:
            errors.append("Fault type selection is required.")
            
        if reported_date:
            try:
                rep_dt = datetime.strptime(reported_date, '%Y-%m-%d')
            except ValueError:
                errors.append("Invalid reported date format.")
                
        if repaired_date:
            try:
                fix_dt = datetime.strptime(repaired_date, '%Y-%m-%d')
                if 'rep_dt' in locals() and fix_dt < rep_dt:
                    errors.append("Repaired date cannot be earlier than reported date.")
            except ValueError:
                errors.append("Invalid repaired date format.")
                
        if errors:
            for err in errors:
                flash(err, 'danger')
            conn.close()
            return render_template(
                'complaint_register.html',
                auto_fault_id=fault_id,
                wards=WARDS,
                fault_types=FAULT_TYPES,
                statuses=STATUSES,
                form_data=request.form
            )
            
        # Determine priority
        if fault_type in ['Transformer Failure', 'Pole Structural Damage']:
            priority = 'Critical'
            need_attention = 1
        elif fault_type in ['Wiring Damage', 'Power Surge']:
            priority = 'High'
            need_attention = 1
        else:
            priority = 'Medium'
            need_attention = 0
            
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO complaints (
                    fault_id, pole_id, ward, street, reported_date,
                    fault_type, status, repaired_date, need_attention, priority
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                fault_id, pole_id, ward, street, reported_date,
                fault_type, status, repaired_date, need_attention, priority
            ))
            conn.commit()
            flash(f"Complaint {fault_id} logged successfully!", 'success')
            conn.close()
            return redirect(url_for('complaints.list_complaints'))
        except Exception as e:
            conn.rollback()
            conn.close()
            flash(f"Database error: {str(e)}", 'danger')
            return render_template(
                'complaint_register.html',
                auto_fault_id=fault_id,
                wards=WARDS,
                fault_types=FAULT_TYPES,
                statuses=STATUSES,
                form_data=request.form
            )
            
    conn.close()
    today_str = datetime.now().strftime('%Y-%m-%d')
    return render_template(
        'complaint_register.html',
        auto_fault_id=auto_fault_id,
        wards=WARDS,
        fault_types=FAULT_TYPES,
        statuses=STATUSES,
        today_str=today_str
    )

@complaints_bp.route('/complaints/<int:complaint_id>')
@login_required
def complaint_details(complaint_id):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
    
    if not row:
        conn.close()
        flash("Complaint not found.", 'danger')
        return redirect(url_for('complaints.list_complaints'))
        
    c = dict(row)
    c['pending_days'] = calculate_pending_days(c['reported_date'], c['repaired_date'], c['status'])
    
    # Check repeat pole report history
    pole_history_count = conn.execute("SELECT COUNT(*) FROM complaints WHERE pole_id = ?", (c['pole_id'],)).fetchone()[0]
    
    conn.close()
    return render_template('complaint_details.html', complaint=c, pole_history_count=pole_history_count, statuses=STATUSES)

@complaints_bp.route('/complaints/<int:complaint_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_complaint(complaint_id):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
    
    if not row:
        conn.close()
        flash("Complaint not found.", 'danger')
        return redirect(url_for('complaints.list_complaints'))
        
    if request.method == 'POST':
        status = request.form.get('status', row['status']).strip()
        repaired_date = request.form.get('repaired_date', '').strip() or None
        ward = request.form.get('ward', row['ward']).strip()
        street = request.form.get('street', row['street']).strip()
        fault_type = request.form.get('fault_type', row['fault_type']).strip()
        
        # Validation
        if status == 'Repaired' and not repaired_date:
            repaired_date = datetime.now().strftime('%Y-%m-%d')
            
        conn.execute("""
            UPDATE complaints 
            SET status = ?, repaired_date = ?, ward = ?, street = ?, fault_type = ?
            WHERE id = ?
        """, (status, repaired_date, ward, street, fault_type, complaint_id))
        conn.commit()
        conn.close()
        
        flash("Complaint updated successfully!", "success")
        return redirect(url_for('complaints.complaint_details', complaint_id=complaint_id))
        
    c = dict(row)
    c['pending_days'] = calculate_pending_days(c['reported_date'], c['repaired_date'], c['status'])
    conn.close()
    return render_template('complaint_details.html', complaint=c, is_edit=True, wards=WARDS, fault_types=FAULT_TYPES, statuses=STATUSES)

@complaints_bp.route('/complaints/<int:complaint_id>/delete', methods=['POST'])
@login_required
def delete_complaint(complaint_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM complaints WHERE id = ?", (complaint_id,))
    conn.commit()
    conn.close()
    flash("Complaint deleted successfully.", "success")
    return redirect(url_for('complaints.list_complaints'))

@complaints_bp.route('/complaints/export')
@login_required
def export_csv():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM complaints ORDER BY id ASC").fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Fault ID', 'Pole ID', 'Ward', 'Street', 'Reported Date', 'Fault Type', 'Status', 'Repaired Date', 'Pending Days'])
    
    for r in rows:
        p_days = calculate_pending_days(r['reported_date'], r['repaired_date'], r['status'])
        writer.writerow([r['fault_id'], r['pole_id'], r['ward'], r['street'], r['reported_date'], r['fault_type'], r['status'], r['repaired_date'] or '', p_days])
        
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=street_light_complaints_export.csv"}
    )
