from flask import Blueprint, render_template, jsonify
from blueprints.auth import login_required
from database import get_db_connection, calculate_pending_days

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    conn = get_db_connection()
    
    # Key Summary Metrics
    total_complaints = conn.execute("SELECT COUNT(*) FROM complaints").fetchone()[0] or 0
    pending_complaints = conn.execute("SELECT COUNT(*) FROM complaints WHERE status IN ('Pending', 'In Progress')").fetchone()[0] or 0
    repaired_complaints = conn.execute("SELECT COUNT(*) FROM complaints WHERE status = 'Repaired'").fetchone()[0] or 0
    
    # Calculate Average Repair Time (server side derived metric)
    repaired_rows = conn.execute("SELECT reported_date, repaired_date FROM complaints WHERE status = 'Repaired' AND repaired_date IS NOT NULL").fetchall()
    repair_times = []
    for r in repaired_rows:
        days = calculate_pending_days(r['reported_date'], r['repaired_date'], 'Repaired')
        repair_times.append(days)
        
    avg_repair_time = round(sum(repair_times) / len(repair_times), 1) if repair_times else 0.0
    
    # Critical / High risk items needing attention
    urgent_complaints = conn.execute("""
        SELECT * FROM complaints 
        WHERE status IN ('Pending', 'In Progress') AND (need_attention = 1 OR priority = 'Critical')
        ORDER BY reported_date ASC LIMIT 5
    """).fetchall()
    
    # Recent complaints
    recent_complaints = conn.execute("""
        SELECT * FROM complaints ORDER BY reported_date DESC, id DESC LIMIT 5
    """).fetchall()
    
    # Annotate derived pending_days
    annotated_recent = []
    for row in recent_complaints:
        r_dict = dict(row)
        r_dict['pending_days'] = calculate_pending_days(r_dict['reported_date'], r_dict['repaired_date'], r_dict['status'])
        annotated_recent.append(r_dict)
        
    annotated_urgent = []
    for row in urgent_complaints:
        r_dict = dict(row)
        r_dict['pending_days'] = calculate_pending_days(r_dict['reported_date'], r_dict['repaired_date'], r_dict['status'])
        annotated_urgent.append(r_dict)
    
    conn.close()
    
    metrics = {
        'total': total_complaints,
        'pending': pending_complaints,
        'repaired': repaired_complaints,
        'avg_repair_time': avg_repair_time
    }
    
    return render_template('dashboard.html', metrics=metrics, recent=annotated_recent, urgent=annotated_urgent)

@dashboard_bp.route('/api/dashboard-charts')
@login_required
def dashboard_charts():
    conn = get_db_connection()
    
    # Complaints by Ward
    ward_rows = conn.execute("SELECT ward, COUNT(*) as count FROM complaints GROUP BY ward ORDER BY ward").fetchall()
    by_ward = {'labels': [r['ward'] for r in ward_rows], 'data': [r['count'] for r in ward_rows]}
    
    # Complaints by Fault Type
    fault_rows = conn.execute("SELECT fault_type, COUNT(*) as count FROM complaints GROUP BY fault_type ORDER BY count DESC").fetchall()
    by_fault = {'labels': [r['fault_type'] for r in fault_rows], 'data': [r['count'] for r in fault_rows]}
    
    # Complaints Status Breakdown
    status_rows = conn.execute("SELECT status, COUNT(*) as count FROM complaints GROUP BY status").fetchall()
    by_status = {'labels': [r['status'] for r in status_rows], 'data': [r['count'] for r in status_rows]}
    
    conn.close()
    
    return jsonify({
        'by_ward': by_ward,
        'by_fault': by_fault,
        'by_status': by_status
    })
