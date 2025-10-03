from flask import Blueprint, render_template, redirect, url_for, flash, request
from app.forms import ProfileForm
from flask_login import login_required, current_user
from sqlalchemy import func
from app import db
from app.models import ServiceProfessionals, Reviews, Users

shared_bp = Blueprint('shared', __name__)

@shared_bp.route('/professional/<int:professional_id>')
def professional_profile(professional_id):
    """
    Displays a public profile page for a service professional,
    including their details and customer reviews.
    """
    professional = ServiceProfessionals.query.get_or_404(professional_id)

    # Query for all reviews for this professional, ordered by newest first
    reviews = Reviews.query.filter_by(
        professional_id=professional.id
    ).order_by(Reviews.created_at.desc()).all()

    # Calculate the professional's average rating
    avg_rating_query = db.session.query(
        func.avg(Reviews.rating)
    ).filter(Reviews.professional_id == professional.id).scalar()
    
    # Round the average rating to one decimal place, handle case with no ratings
    avg_rating = round(avg_rating_query, 1) if avg_rating_query else None

    return render_template(
        'shared/professional_profile.html',
        professional=professional,
        reviews=reviews,
        avg_rating=avg_rating
    )

@shared_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """
    Allows the currently logged-in user (customer or professional)
    to edit their own profile information.
    """
    user = current_user
    form = ProfileForm(original_username=user.username, original_email=user.email)

    if form.validate_on_submit():
        # Update user data from form
        user.username = form.username.data
        user.email = form.email.data
        user.address = form.address.data
        user.pin = form.pin.data
        
        # Optionally update password if a new one was entered
        if form.password.data:
            user.set_password(form.password.data)

        # Update professional-specific data if the user is a professional
        if user.role == 'professional' and user.professional:
            user.professional.description = form.description.data
            user.professional.experience = form.experience.data
        
        db.session.commit()
        flash('Your profile has been updated successfully!', 'success')

        # Redirect back to their respective dashboards
        if user.role == 'customer':
            return redirect(url_for('customer.customer_profile', customer_id=user.customer.id))
        elif user.role == 'professional':
            return redirect(url_for('shared.professional_profile', professional_id=user.professional.id))
        else: # Fallback for admin
            return redirect(url_for('admin.admin_dashboard'))

    # Pre-populate the form with the user's current data on GET request
    elif request.method == 'GET':
        form.username.data = user.username
        form.email.data = user.email
        form.address.data = user.address
        form.pin.data = user.pin
        if user.role == 'professional' and user.professional:
            form.description.data = user.professional.description
            form.experience.data = user.professional.experience
            
    return render_template('shared/edit_profile.html', form=form)