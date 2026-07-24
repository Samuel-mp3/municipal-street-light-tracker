from flask import Blueprint, render_template, jsonify, request
from blueprints.auth import login_required
from database import get_db_connection, calculate_pending_days

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/reports')
@login_required
def index():
    conn = get_db_connection()
    
    # 1. Ward Wise Aggregates
    ward_rows = conn.execute("""
        SELECT ward, 
               COUNT(*) as total,
               SUM(CASE WHEN status IN ('Pending', 'In Progress') THEN 1 ELSE 0 END) as pending,
               SUM(CASE WHEN status = 'Repaired' THEN 1 ELSE 0 END) as repaired,
               SUM(CASE WHEN need_attention = 1 THEN 1 ELSE 0 END) as urgent
        FROM complaints 
        GROUP BY ward 
        ORDER BY total DESC
    """).fetchall()
    
    # 2. Fault Type Aggregates
    fault_rows = conn.execute("""
        SELECT fault_type, 
               COUNT(*) as total,
               SUM(CASE WHEN status IN ('Pending', 'In Progress') THEN 1 ELSE 0 END) as pending,
               SUM(CASE WHEN status = 'Repaired' THEN 1 ELSE 0 END) as repaired
        FROM complaints 
        GROUP BY fault_type 
        ORDER BY total DESC
    """).fetchall()
    
    # 3. Monthly Aggregates
    monthly_rows = conn.execute("""
        SELECT strftime('%Y-%m', reported_date) as month,
               COUNT(*) as total,
               SUM(CASE WHEN status = 'Repaired' THEN 1 ELSE 0 END) as repaired,
               SUM(CASE WHEN status IN ('Pending', 'In Progress') THEN 1 ELSE 0 END) as pending
        FROM complaints
        GROUP BY month
        ORDER BY month ASC
    """).fetchall()
    
    # Calculate average repair days per ward (server-side calculation)
    all_repaired = conn.execute("""
        SELECT ward, reported_date, repaired_date FROM complaints WHERE status = 'Repaired' AND repaired_date IS NOT NULL
    """).fetchall()
    
    ward_repair_days = {}
    for r in all_repaired:
        w = r['ward']
        days = calculate_pending_days(r['reported_date'], r['repaired_date'], 'Repaired')
        ward_repair_days.setdefault(w, []).append(days)
        
    ward_avg_days = {w: round(sum(days_list) / len(days_list), 1) for w, days_list in ward_repair_days.items()}
    
    # Annotate ward_rows with avg_repair_days
    ward_summary = []
    for r in ward_rows:
        w_dict = dict(r)
        w_dict['avg_repair_days'] = ward_avg_days.get(w_dict['ward'], 0.0)
        ward_summary.append(w_dict)
        
    conn.close()
    
    return render_template(
        'reports.html',
        ward_summary=ward_summary,
        fault_summary=[dict(r) for r in fault_rows],
        monthly_summary=[dict(r) for r in monthly_rows]
    )

@reports_bp.route('/api/reports/chart-data')
@login_required
def reports_chart_data():
    conn = get_db_connection()
    
    # Ward distribution
    ward_rows = conn.execute("SELECT ward, COUNT(*) as count FROM complaints GROUP BY ward ORDER BY ward").fetchall()
    
    # Fault type breakdown
    fault_rows = conn.execute("SELECT fault_type, COUNT(*) as count FROM complaints GROUP BY fault_type ORDER BY count DESC").fetchall()
    
    # Monthly trend breakdown
    monthly_rows = conn.execute("""
        SELECT strftime('%Y-%m', reported_date) as month, COUNT(*) as total,
               SUM(CASE WHEN status = 'Repaired' THEN 1 ELSE 0 END) as repaired,
               SUM(CASE WHEN status IN ('Pending', 'In Progress') THEN 1 ELSE 0 END) as pending
        FROM complaints
        GROUP BY month
        ORDER BY month ASC
    """).fetchall()
    
    conn.close()
    
    return jsonify({
        'ward': {
            'labels': [r['ward'] for r in ward_rows],
            'datasets': [{'label': 'Total Complaints', 'data': [r['count'] for r in ward_rows]}]
        },
        'fault': {
            'labels': [r['fault_type'] for r in fault_rows],
            'datasets': [{'label': 'Fault Types', 'data': [r['count'] for r in fault_rows]}]
        },
        'monthly': {
            'labels': [r['month'] or 'Unknown' for r in monthly_rows],
            'datasets': [
                {'label': 'Total Reported', 'data': [r['total'] for r in monthly_rows]},
                {'label': 'Repaired', 'data': [r['repaired'] for r in monthly_rows]},
                {'label': 'Pending', 'data': [r['pending'] for r in monthly_rows]}
            ]
        }
    })
