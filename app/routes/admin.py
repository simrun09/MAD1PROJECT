from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from app import db
from sqlalchemy import or_, func
from app.models import Users, Customers, ServiceProfessionals, Services, ServiceRequests, Reviews, ServiceStatus
from app.forms import CreateServiceForm, UpdateServiceForm

admin_bp = Blueprint('admin', __name__)

# --- Admin Role Protection Decorator ---
def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.role != 'admin':
            # Abort with a 403 Forbidden error if the user is not an admin
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

# --- Routes ---

@admin_bp.route("/dashboard")
@admin_required
def admin_dashboard():
    """Main dashboard to view all data."""
    services = Services.query.all()
    professionals = ServiceProfessionals.query.join(Users).filter(Users.role == 'professional').all()
    customers = Customers.query.join(Users).filter(Users.role == 'customer').all()
    all_requests = ServiceRequests.query.filter(
    ServiceRequests.service_status.in_([
        ServiceStatus.REQUESTED, 
        ServiceStatus.ACCEPTED, 
        ServiceStatus.CLOSED, 
        ServiceStatus.PAID
    ])).all()
    rejected_requests = ServiceRequests.query.filter_by(service_status=ServiceStatus.REJECTED).all()
    return render_template(
        "admin/admin_dashboard.html",
        services=services,
        professionals=professionals,
        customers=customers,
        all_requests=all_requests,
        rejected_requests=rejected_requests
    )

# --- Service Management ---

@admin_bp.route("/services/create", methods=["POST"])
@admin_required
def create_service():
    """Creates a new service type from the modal form."""
    form = CreateServiceForm()
    
    # The form handles all validation, including uniqueness
    if form.validate_on_submit():
        new_service = Services(
            service_type=form.service_type.data,
            base_price=form.base_price.data,
            description=form.description.data
        )
        db.session.add(new_service)
        db.session.commit()
        flash(f"Service '{form.service_type.data}' created successfully.", "success")
    else:
        # If validation fails, flash the first error
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{getattr(form, field).label.text}: {error}", 'danger')
                break # Flash only the first error
            break

    return redirect(url_for("admin.admin_dashboard"))

@admin_bp.route("/services/<int:service_id>/update", methods=["POST"])
@admin_required
def update_service(service_id):
    """Updates an existing service's details."""
    service_to_update = Services.query.get_or_404(service_id)
    form = UpdateServiceForm(original_service_type=service_to_update.service_type)

    if form.validate_on_submit():
        service_to_update.service_type = form.service_type.data
        service_to_update.base_price = form.base_price.data
        service_to_update.description = form.description.data
        db.session.commit()
        flash(f"Service '{service_to_update.service_type}' updated successfully.", "success")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Update failed for {service_to_update.service_type} - {getattr(form, field).label.text}: {error}", 'danger')
                break
            break
    
    return redirect(url_for("admin.admin_dashboard"))

@admin_bp.route("/services/<int:service_id>/delete", methods=["POST"])
@admin_required
def delete_service(service_id):
    """Deletes a service."""
    service = Services.query.get_or_404(service_id)
    
    # Check if any professionals are assigned to this service before deleting
    if len(service.professionals) > 0:
        flash(f"Cannot delete '{service.service_type}' as professionals are still assigned to it.", "danger")
        return redirect(url_for("admin.admin_dashboard"))

    db.session.delete(service)
    db.session.commit()
    flash(f"Service '{service.service_type}' has been deleted.", "success")
    return redirect(url_for("admin.admin_dashboard"))


# --- Professional Management ---

@admin_bp.route('/professionals/<int:professional_id>/approve', methods=['POST'])
@admin_required
def approve_professional(professional_id):
    prof = ServiceProfessionals.query.get_or_404(professional_id)
    prof.is_verified = True
    prof.verification_failed = False
    db.session.commit()
    flash(f'Professional {prof.user.username} has been approved.', 'success')
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/professionals/<int:professional_id>/reject', methods=['POST'])
@admin_required
def reject_professional(professional_id):
    prof = ServiceProfessionals.query.get_or_404(professional_id)
    prof.is_verified = False
    prof.verification_failed = True
    db.session.commit()
    flash(f'Professional {prof.user.username} has been rejected.', 'warning')
    return redirect(url_for('admin.admin_dashboard'))

# --- User Management (Block/Unblock) ---

@admin_bp.route('/users/<int:user_id>/block', methods=['POST'])
@admin_required
def block_user(user_id):
    user = Users.query.get_or_404(user_id)
    if user.role == 'customer':
        user.customer.admin_blocked = True
    elif user.role == 'professional':
        user.professional.admin_blocked = True
    db.session.commit()
    flash(f'User {user.username} has been blocked.', 'success')
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/users/<int:user_id>/unblock', methods=['POST'])
@admin_required
def unblock_user(user_id):
    user = Users.query.get_or_404(user_id)
    if user.role == 'customer':
        user.customer.admin_blocked = False
    elif user.role == 'professional':
        user.professional.admin_blocked = False
    db.session.commit()
    flash(f'User {user.username} has been unblocked.', 'info')
    return redirect(url_for('admin.admin_dashboard'))


@admin_bp.route("/search")
@admin_required
def admin_search():
    search_params = {
        'category': request.args.get('category'),
        'q': request.args.get('q', '').strip()
    }
    results = None

    if search_params['category'] and search_params['q']:
        search_term = f"%{search_params['q']}%"
        
        if search_params['category'] == 'professional':
            results = ServiceProfessionals.query.join(Users).filter(or_(
                Users.username.ilike(search_term),
                Users.email.ilike(search_term),
                Users.address.ilike(search_term),
                Users.pin.ilike(search_term)
            )).all()
        elif search_params['category'] == 'customer':
            results = Customers.query.join(Users).filter(or_(
                Users.username.ilike(search_term),
                Users.email.ilike(search_term),
                Users.address.ilike(search_term),
                Users.pin.ilike(search_term)
            )).all()

    return render_template("admin/admin_search.html", search_params=search_params, results=results)


@admin_bp.route("/charts/data")
@admin_required
def admin_chart_data():
    """Provides data for the admin dashboard charts."""
    
    # Query for service requests by status
    status_counts = db.session.query(
        ServiceRequests.service_status, func.count(ServiceRequests.id)
    ).group_by(ServiceRequests.service_status).all()
    
    # Query for ratings distribution
    rating_counts = db.session.query(
        Reviews.rating, func.count(Reviews.id)
    ).group_by(Reviews.rating).all()
    
    # Format data for Chart.js
    requests_chart_data = {
        'labels': [status.name.title() for status, count in status_counts],
        'data': [count for status, count in status_counts]
    }
    
    ratings_chart_data = {
        'labels': [f'{rating}-Star' for rating, count in rating_counts],
        'data': [count for rating, count in rating_counts]
    }
    
    return jsonify({
        'requests_by_status': requests_chart_data,
        'ratings_distribution': ratings_chart_data
    })

@admin_bp.route('/request/<int:request_id>/reassign', methods=['POST'])
@admin_required
def reassign_professional(request_id):
    """Reassigns a rejected request to a new professional."""
    service_request = ServiceRequests.query.get_or_404(request_id)
    new_prof_id = request.form.get('professional_id', type=int)

    if not new_prof_id:
        flash('You must select a professional to reassign to.', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    # Security check: Ensure the request was actually rejected
    if service_request.service_status != ServiceStatus.REJECTED:
        flash('This request is not in a state that can be reassigned.', 'warning')
        return redirect(url_for('admin.admin_dashboard'))
    
    # Update the request with the new professional and reset the status
    service_request.professional_id = new_prof_id
    service_request.service_status = ServiceStatus.REQUESTED # This is key!
    
    db.session.commit()
    flash(f'Request #{service_request.id} has been successfully reassigned. The new professional has been notified.', 'success')
    return redirect(url_for('admin.admin_dashboard'))