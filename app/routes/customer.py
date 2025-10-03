from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user, logout_user
from sqlalchemy import func, or_
from app import db
from app.models import Users, Customers, Services, ServiceProfessionals, ServiceRequests, Reviews, ServiceStatus
from app.forms import ReviewForm, BookingForm, UpdateRequestForm

customer_bp = Blueprint('customer', __name__)

# --- Customer Role Protection Decorator ---
def customer_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.role != 'customer':
            abort(403) # Forbidden
        
        # --- THIS IS THE NEW BLOCKING LOGIC ---
        if current_user.customer and current_user.customer.admin_blocked:
            flash("Your account has been suspended by an administrator.", "danger")
            logout_user() # Log them out immediately
            return redirect(url_for('auth.login'))
        
        return f(*args, **kwargs)
    return decorated_function
# --- Routes ---

@customer_bp.route("/dashboard")
@customer_required
def customer_dashboard():
    form = BookingForm()
    all_services = Services.query.order_by(Services.service_type).all()
    
    # --- Search Logic ---
    search_params = {
        'service_id': request.args.get('service_id', type=int),
        'q': request.args.get('q', type=str, default="").strip()
    }

    # Start with a base query for verified, non-blocked professionals
    query = ServiceProfessionals.query.join(Users).filter(
        ServiceProfessionals.is_verified == True,
        ServiceProfessionals.admin_blocked == False
    )

    # Apply filters based on search parameters
    if search_params['service_id']:
        query = query.filter(ServiceProfessionals.service_id == search_params['service_id'])
    
    if search_params['q']:
        search_term = f"%{search_params['q']}%"
        query = query.filter(or_(
            Users.username.ilike(search_term),
            Users.address.ilike(search_term),
            Users.pin.ilike(search_term)
        ))

    professionals = query.all()
    
    # --- Data for Template ---
    avg_ratings = {}
    selected_service_name = ""
    if search_params['service_id']:
        service = Services.query.get(search_params['service_id'])
        if service:
            selected_service_name = service.service_type

    if professionals:
        prof_ids = [p.id for p in professionals]
        ratings_query = db.session.query(
            Reviews.professional_id,
            func.avg(Reviews.rating).label('average_rating')
        ).filter(Reviews.professional_id.in_(prof_ids)).group_by(Reviews.professional_id).all()
        avg_ratings = {prof_id: round(avg, 1) for prof_id, avg in ratings_query}

    return render_template(
        'customer/customer_dashboard.html',
        form=form,
        all_services=all_services,
        professionals=professionals,
        avg_ratings=avg_ratings,
        selected_service_id=search_params['service_id'], # Pass the service_id for the modal
        selected_service_name=selected_service_name,
        search_params=search_params # Pass search terms back to the template
    )

@customer_bp.route('/book_service/<int:professional_id>', methods=['POST'])
@customer_required
def book_service(professional_id):
    form = BookingForm() # Instantiate the form
    professional = ServiceProfessionals.query.get_or_404(professional_id)

    if form.validate_on_submit():
        # Check for existing active requests
        existing_request = ServiceRequests.query.filter(
            ServiceRequests.customer_id == current_user.customer.id,
            ServiceRequests.professional_id == professional.id,
            ServiceRequests.service_status.in_([ServiceStatus.REQUESTED, ServiceStatus.ACCEPTED])
        ).first()

        if existing_request:
            flash('You already have an active request with this professional.', 'warning')
            return redirect(url_for('customer.customer_dashboard', service_id=form.service_id.data))

        new_request = ServiceRequests(
            service_id=form.service_id.data,
            customer_id=current_user.customer.id,
            professional_id=professional.id,
            proposed_price=form.proposed_price.data,
            service_status=ServiceStatus.REQUESTED
        )
        db.session.add(new_request)
        db.session.commit()
        flash('Your service request has been sent!', 'success')
        return redirect(url_for('customer.service_history'))
    else:
        flash('There was an error with your booking request. Please try again.', 'danger')
        return redirect(url_for('customer.customer_dashboard'))

@customer_bp.route('/request/<int:request_id>/update', methods=['POST'])
@customer_required
def update_service_request(request_id):
    service_request = ServiceRequests.query.get_or_404(request_id)
    form = UpdateRequestForm()

    # Security checks remain the same
    if service_request.customer_id != current_user.customer.id:
        abort(403)
    if service_request.service_status != ServiceStatus.REQUESTED:
        flash('You can only edit requests that are still pending.', 'warning')
        return redirect(url_for('customer.service_history'))
    
    if form.validate_on_submit():
        service_request.proposed_price = form.proposed_price.data
        db.session.commit()
        flash('Your service request has been updated successfully.', 'success')
    else:
        flash('Invalid price submitted. Please provide a valid number.', 'danger')

    return redirect(url_for('customer.service_history'))

@customer_bp.route('/service_history')
@customer_required
def service_history():
    form = UpdateRequestForm() # Create an instance of the form
    service_requests = ServiceRequests.query.filter_by(
        customer_id=current_user.customer.id
    ).order_by(ServiceRequests.created_at.desc()).all()
    return render_template('customer/service_history.html', service_requests=service_requests, form=form)


@customer_bp.route('/review_service/<int:request_id>', methods=['POST'])
@customer_required
def review_service(request_id):
    service_request = ServiceRequests.query.get_or_404(request_id)
    form = ReviewForm() # Instantiate the form

    # ... (security checks are the same) ...
    
    # Use the form to validate
    if form.validate_on_submit():
        new_review = Reviews(
            customer_id=current_user.customer.id,
            professional_id=service_request.professional_id,
            service_id=service_request.service_id,
            service_request_id=service_request.id,
            rating=form.rating.data, # Use validated data from the form
            remarks=form.remarks.data
        )
        # ... (update service_request status and commit) ...
        flash('Thank you for your review!', 'success')
    else:
        flash('There was an error with your review submission.', 'danger')
        
    return redirect(url_for('customer.service_history'))

@customer_bp.route('/payment/<int:request_id>', methods=['GET'])
@customer_required
def show_payment_form(request_id):
    service_request = ServiceRequests.query.get_or_404(request_id)
    # Security checks
    if service_request.customer_id != current_user.customer.id:
        abort(403)
    if service_request.service_status != ServiceStatus.CLOSED:
        flash("This service is not yet closed for payment.", "warning")
        return redirect(url_for('customer.service_history'))
        
    return render_template('customer/payment.html', service_request=service_request)

@customer_bp.route('/payment/<int:request_id>/process', methods=['POST'])
@customer_required
def process_payment(request_id):
    service_request = ServiceRequests.query.get_or_404(request_id)
    # Security checks
    if service_request.customer_id != current_user.customer.id:
        abort(403)
    if service_request.service_status != ServiceStatus.CLOSED:
        flash("This service cannot be paid for at this time.", "warning")
        return redirect(url_for('customer.service_history'))

    # In a real app, you'd process the payment here.
    # We will just update the status.
    service_request.service_status = ServiceStatus.PAID
    db.session.commit()
    
    flash(f"Payment for request #{service_request.id} was successful! Thank you.", "success")
    return redirect(url_for('customer.service_history'))



@customer_bp.route('/profile/<int:customer_id>')
@login_required # Must be logged in
def customer_profile(customer_id):
    """
    Displays a customer's profile and service history.
    Accessible only by the customer themselves or an admin.
    """
    customer = Customers.query.get_or_404(customer_id)

    # --- SECURITY CHECK ---
    # Allow access if the current user is an admin OR if they are the customer viewing their own profile.
    if current_user.role != 'admin' and current_user.id != customer.user_id:
        abort(403) # Forbidden

    # Query for all of this customer's requests to show their history
    service_requests = ServiceRequests.query.filter_by(
        customer_id=customer.id
    ).order_by(ServiceRequests.created_at.desc()).all()
    
    return render_template(
        'customer/customer_profile.html',
        customer=customer,
        service_requests=service_requests
    )