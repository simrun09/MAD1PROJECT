import enum
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db, login_manager  # ### REFINEMENT ### Import db and login_manager from our app package
import secrets


# ### REFINEMENT ### This function is required by Flask-Login to load a user from the database by their ID.
# It connects the user session to the actual user object.
@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))

# ----------------------------
# Base Model (timestamps)
# ----------------------------
class BaseModel(db.Model):
    __abstract__ = True
    # ### REFINEMENT ### Using datetime.utcnow is good, but for future-proofing with different server timezones,
    # it's slightly better to import timezone from datetime and use datetime.now(timezone.utc).
    # However, since you are consistent, we will stick with your implementation. `utcnow` is perfectly fine here.
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# ----------------------------
# Users
# ----------------------------
# ### REFINEMENT ### Your class already inherits from UserMixin, which provides default implementations
# for required Flask-Login attributes like is_authenticated, is_active, etc.
class Users(UserMixin, BaseModel):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, index=True, nullable=False)
    email = db.Column(db.String(120), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False) # ### REFINEMENT ### Increased length for future-proofing with newer hashing algorithms.
    role = db.Column(db.String(50), index=True, nullable=False)  # admin, customer, professional
    address = db.Column(db.String(200), nullable=True, index=True)
    pin = db.Column(db.String(20), nullable=True, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    api_key = db.Column(db.String(32), unique=True, nullable=True, index=True)

    # Relationships
    customer = db.relationship("Customers", back_populates="user", uselist=False, cascade="all, delete-orphan")
    professional = db.relationship("ServiceProfessionals", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
     return f"<User '{self.username}'>"
    def generate_api_key(self):
        """Generates a new unique API key for the user."""
        self.api_key = secrets.token_hex(16)
        return self.api_key
    # ### REFINEMENT ### Flask-Login's UserMixin already has a get_id() method that does this, so we can remove the explicit one.

    # Password methods
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# ----------------------------
# Customers
# ----------------------------
class Customers(BaseModel):
    __tablename__ = 'customers'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    admin_blocked = db.Column(db.Boolean, default=False, nullable=False)

    user = db.relationship("Users", back_populates="customer")
    service_requests = db.relationship("ServiceRequests", back_populates="customer", cascade="all, delete-orphan")
    reviews = db.relationship("Reviews", back_populates="customer", cascade="all, delete-orphan")


# ----------------------------
# Services
# ----------------------------
class Services(BaseModel):
    __tablename__ = 'services'

    id = db.Column(db.Integer, primary_key=True)
    service_type = db.Column(db.String(80), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    base_price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(255), nullable=True)

    professionals = db.relationship("ServiceProfessionals", back_populates="service") # ### REFINEMENT ### Removed cascade here. Deleting a service should not automatically delete professionals. It's better to handle this logic explicitly (e.g., prevent service deletion if professionals are assigned).
    service_requests = db.relationship("ServiceRequests", back_populates="service")
    reviews = db.relationship("Reviews", back_populates="service")

    def __repr__(self):
     return f"<Service '{self.service_type}'>"
# ----------------------------
# Service Professionals
# ----------------------------
class ServiceProfessionals(BaseModel):
    __tablename__ = 'service_professionals'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=False) # ### REFINEMENT ### Removed ondelete="CASCADE". Same reason as above.
    description = db.Column(db.Text, nullable=True)
    experience = db.Column(db.Integer, nullable=True)
    document = db.Column(db.String(255), nullable=True)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    verification_failed = db.Column(db.Boolean, default=False, nullable=False)
    admin_blocked = db.Column(db.Boolean, default=False, nullable=False)

    user = db.relationship("Users", back_populates="professional")
    service = db.relationship("Services", back_populates="professionals")
    service_requests = db.relationship("ServiceRequests", back_populates="professional", cascade="all, delete-orphan")
    reviews = db.relationship("Reviews", back_populates="professional", cascade="all, delete-orphan")


# ----------------------------
# Enum for Service Status
# ----------------------------
class ServiceStatus(enum.Enum):
    REQUESTED = "requested"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CLOSED = "closed"
    PAID = "paid"


# ----------------------------
# Service Requests
# ----------------------------
class ServiceRequests(BaseModel):
    __tablename__ = 'service_requests'

    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False, index=True)
    professional_id = db.Column(db.Integer, db.ForeignKey("service_professionals.id"), nullable=True, index=True) # ### REFINEMENT ### Changed to nullable=True. A request can exist before a professional is assigned by the admin.

    proposed_price = db.Column(db.Float, nullable=True)
    date_of_request = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    date_of_completion = db.Column(db.DateTime, nullable=True)
    service_status = db.Column(db.Enum(ServiceStatus), default=ServiceStatus.REQUESTED, nullable=False, index=True)
    remarks = db.Column(db.Text, nullable=True) # ### REFINEMENT ### Moved this from Reviews to here, as remarks are on the service itself.

    service = db.relationship("Services", back_populates="service_requests")
    customer = db.relationship("Customers", back_populates="service_requests")
    professional = db.relationship("ServiceProfessionals", back_populates="service_requests")
    review = db.relationship("Reviews", back_populates="service_request", uselist=False, cascade="all, delete-orphan") # ### REFINEMENT ### Changed to 'review' (singular) and uselist=False for a one-to-one relationship.

    def __repr__(self):
     return f"<ServiceRequest id={self.id}>"
# ----------------------------
# Reviews
# ----------------------------
class Reviews(BaseModel):
    __tablename__ = 'reviews'

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False, index=True)
    professional_id = db.Column(db.Integer, db.ForeignKey("service_professionals.id"), nullable=False, index=True)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=False, index=True)
    service_request_id = db.Column(db.Integer, db.ForeignKey("service_requests.id"), unique=True, nullable=False)

    rating = db.Column(db.Integer, db.CheckConstraint('rating >= 1 AND rating <= 5'), nullable=False)
    remarks = db.Column(db.Text, nullable=True) # ### REFINEMENT ### Keeping remarks here as well for specific review comments.

    customer = db.relationship("Customers", back_populates="reviews")
    professional = db.relationship("ServiceProfessionals", back_populates="reviews")
    service = db.relationship("Services", back_populates="reviews")
    service_request = db.relationship("ServiceRequests", back_populates="review")