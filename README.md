# TravelGo - Travel Booking Platform

A comprehensive travel booking platform built with Flask and AWS services, enabling users to search and book flights, hotels, trains, and buses.

## 🚀 Features

- **Multi-Modal Transportation Booking**: Book flights, hotels, trains, and buses
- **User Authentication**: Secure registration and login system
- **Search Functionality**:
  - Simple search by source and destination
  - Multi-hop journey planning
  - Budget-based search
- **Booking Management**: View, manage, and cancel bookings
- **Real-Time Notifications**: SNS-based email notifications for booking confirmations and cancellations
- **Admin Dashboard**: Manage transportation inventory and view analytics
- **PDF Tickets**: Generate and download booking tickets with QR codes
- **Payment Integration**: Simulated payment processing

## 🛠️ Technology Stack

### Backend

- **Flask 3.0**: Python web framework
- **Python 3.x**: Core programming language

### AWS Services

- **DynamoDB**: NoSQL database for persistent storage
- **SNS (Simple Notification Service)**: Real-time email notifications
- **IAM**: Identity and Access Management for secure service access

### Frontend

- **HTML/CSS**: Responsive UI templates
- **JavaScript**: Dynamic autocomplete and interactivity
- **Jinja2**: Template engine

### Libraries

- **boto3**: AWS SDK for Python
- **Werkzeug**: Password hashing and security
- **xhtml2pdf**: PDF ticket generation
- **qrcode**: QR code generation for tickets

## 📁 Project Structure

```
travelgo/
├── app.py                      # Main application entry point
├── config.py                   # Configuration settings
├── models.py                   # DynamoDB model classes
├── seed.py                     # Database initialization and seeding
├── requirements.txt            # Python dependencies
├── routes/                     # Route handlers
│   ├── __init__.py
│   ├── main.py                # Home and dashboard routes
│   ├── search.py              # Search functionality
│   ├── booking.py             # Booking management
│   ├── auth.py                # Authentication routes
│   ├── admin.py               # Admin panel routes
│   ├── notifications.py       # Notification management
│   └── api.py                 # API endpoints
├── templates/                  # HTML templates
│   ├── base.html
│   ├── home.html
│   ├── search.html
│   ├── results.html
│   ├── booking.html
│   ├── confirmation.html
│   ├── dashboard.html
│   ├── profile.html
│   ├── admin.html
│   └── ...
├── static/                     # Static assets
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── autocomplete.js
│   └── images/
├── data/                       # Initial seed data
│   ├── flights.json
│   ├── hotels.json
│   ├── trains.json
│   └── buses.json
└── utils/                      # Utility functions
    └── email.py
```

## 🗄️ Database Schema

### DynamoDB Tables

1. **travelgo-users**
   - Partition Key: `_id` (String, UUID)
   - GSIs: `email-index`, `username-index`
   - Attributes: username, email, password_hash, full_name, phone, created_at

2. **travelgo-flights**
   - Partition Key: `_id` (String, UUID)
   - Attributes: flight_number, airline, source, destination, departure_time, arrival_time, price, available_seats, flight_class

3. **travelgo-hotels**
   - Partition Key: `_id` (String, UUID)
   - Attributes: hotel_name, location, room_type, price_per_night, available_rooms, amenities, rating

4. **travelgo-trains**
   - Partition Key: `_id` (String, UUID)
   - Attributes: train_number, train_name, source, destination, departure_time, arrival_time, price, available_seats, class_type

5. **travelgo-buses**
   - Partition Key: `_id` (String, UUID)
   - Attributes: bus_number, operator, source, destination, departure_time, arrival_time, price, available_seats, bus_type

6. **travelgo-bookings**
   - Partition Key: `_id` (String, UUID)
   - GSI: `user_id-index`
   - Attributes: user_id, booking_type, item_id, booking_details, total_amount, status, created_at, paid_at

7. **travelgo-notifications**
   - Partition Key: `_id` (String, UUID)
   - GSI: `user_id-index`
   - Attributes: user_id, message, notification_type, is_read, created_at

## 🚦 Application Flow

### 1. User Registration & Authentication

```
User Registration → Password Hashing (Werkzeug) → Store in DynamoDB (users table)
User Login → Verify Credentials → Create Session → Redirect to Dashboard
```

### 2. Search Flow

```
User Enters Search Criteria (Source, Destination, Date)
↓
Backend Queries Multiple Tables (flights, hotels, trains, buses)
↓
Filter by Criteria and Sort by Price/Time
↓
Display Results with Availability
```

### 3. Booking Flow

```
User Selects Transportation/Hotel
↓
Enter Passenger/Guest Details
↓
Payment Processing (Simulated)
↓
Create Booking Record in DynamoDB
↓
Update Available Seats/Rooms
↓
Send SNS Notification (Email Confirmation)
↓
Generate PDF Ticket with QR Code
↓
Redirect to Confirmation Page
```

### 4. Booking Management

```
User Views Dashboard → Fetch Bookings from DynamoDB
↓
User Can:
- View Booking Details
- Download PDF Ticket
- Cancel Booking → Update Status → Refund Processing → SNS Notification
```

### 5. Admin Flow

```
Admin Login → Admin Dashboard
↓
View Analytics (Total Bookings, Revenue, Users)
↓
Manage Inventory:
- Add/Update/Delete Flights/Hotels/Trains/Buses
- View Booking Reports
```

### 6. Notification Flow

```
Booking Event (Create/Cancel)
↓
Publish to SNS Topic (arn:aws:sns:ap-south-1:336449003024:TravelGoNotifications)
↓
SNS Delivers Email to User
↓
Store Notification in DynamoDB (notifications table)
↓
User Can View in Notifications Page
```

## ⚙️ Configuration

All configuration is hardcoded in `config.py`:

- `SECRET_KEY`: Flask session encryption key
- `AWS_REGION`: ap-south-1 (Mumbai)
- `SNS_TOPIC_ARN`: TravelGo notification topic
- `DYNAMO_TABLE_PREFIX`: travelgo

## 🔧 Setup Instructions

### Prerequisites

- Python 3.8 or higher
- AWS Account with:
  - DynamoDB access
  - SNS access
  - IAM role (for EC2 deployment)

### Local Development

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd travelgo
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure AWS Credentials**

   For local development, configure AWS CLI:

   ```bash
   aws configure
   ```

   Enter your AWS Access Key ID, Secret Access Key, and region (ap-south-1).

4. **Initialize Database**

   ```bash
   python seed.py
   ```

   This will:
   - Create 7 DynamoDB tables with proper schemas and GSIs
   - Seed 50 sample records for flights, hotels, trains, and buses

5. **Run the application**
   ```bash
   python app.py
   ```
   Access the application at `http://localhost:5000`

### AWS EC2 Deployment

1. **Launch EC2 Instance**
   - AMI: Ubuntu 20.04 or Amazon Linux 2
   - Instance Type: t2.micro or higher
   - Security Group: Allow inbound traffic on ports 22 (SSH) and 5000 (Flask)

2. **Attach IAM Role**

   Create an IAM role with the following policies:
   - `AmazonDynamoDBFullAccess`
   - `AmazonSNSFullAccess`

   Attach this role to your EC2 instance. The application will automatically use IAM role credentials (no need for access keys).

3. **Connect to EC2 via SSH**

   ```bash
   ssh -i your-key.pem ec2-user@your-ec2-ip
   ```

4. **Install Python and Git**

   ```bash
   sudo yum update -y  # For Amazon Linux
   sudo yum install python3 git -y
   ```

5. **Clone and Setup**

   ```bash
   git clone <repository-url>
   cd travelgo
   pip3 install -r requirements.txt
   ```

6. **Initialize Database**

   ```bash
   python3 seed.py
   ```

7. **Run Application**

   ```bash
   python3 app.py
   ```

   For production, use Gunicorn:

   ```bash
   pip3 install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

8. **Access Application**
   ```
   http://your-ec2-public-ip:5000
   ```

## 🔐 Security Notes

- **No Credentials in Code**: The application uses IAM roles for EC2 deployment
- **Password Security**: User passwords are hashed using Werkzeug's PBKDF2
- **Session Management**: Flask sessions with secure secret key
- **Production Deployment**: Use HTTPS, environment variables, and proper secret management

## 📝 API Endpoints

### Public Routes

- `GET /` - Home page
- `GET /login` - Login page
- `POST /login` - Authenticate user
- `GET /register` - Registration page
- `POST /register` - Create new user

### Protected Routes (Requires Login)

- `GET /dashboard` - User dashboard
- `GET /search` - Search page
- `POST /search` - Perform search
- `GET /booking/<type>/<id>` - Booking form
- `POST /process-booking` - Process booking
- `GET /bookings` - View user bookings
- `POST /cancel-booking/<id>` - Cancel booking
- `GET /download-ticket/<booking_id>` - Download PDF ticket
- `GET /notifications` - View notifications

### Admin Routes

- `GET /admin` - Admin dashboard
- `POST /admin/add-<type>` - Add transportation/hotel
- `POST /admin/update-<type>/<id>` - Update item
- `DELETE /admin/delete-<type>/<id>` - Delete item

### API Routes

- `GET /api/autocomplete?type=<type>&term=<term>` - Autocomplete suggestions
- `GET /api/search-locations?type=<type>&term=<term>` - Location search

## 🧪 Testing

The application has been thoroughly tested without AWS credentials to verify:

- ✅ All route handlers work correctly
- ✅ Model methods properly interface with DynamoDB
- ✅ SNS notifications are properly wrapped in try/except blocks
- ✅ No reserved word conflicts in DynamoDB queries
- ✅ Datetime serialization works correctly
- ✅ PDF generation and QR codes function properly

## 📊 Sample Data

The `seed.py` script generates:

- **50 Flights**: Various airlines, routes, and classes
- **50 Hotels**: Different locations, room types, and amenities
- **50 Trains**: Multiple routes and class types
- **50 Buses**: Different operators and bus types

All with realistic prices, timings, and availability.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/YourFeature`)
3. Commit your changes (`git commit -m 'Add YourFeature'`)
4. Push to the branch (`git push origin feature/YourFeature`)
5. Open a Pull Request

## 📄 License

This project is for educational purposes.

## 👨‍💻 Author

TravelGo - Travel Booking Platform

## 🔗 AWS Resources

- **DynamoDB Tables**: 7 tables in ap-south-1 region
- **SNS Topic**: arn:aws:sns:ap-south-1:336449003024:TravelGoNotifications
- **Region**: ap-south-1 (Asia Pacific - Mumbai)

---

**Note**: Ensure your EC2 instance has the proper IAM role attached before running the application. The application will not work without proper AWS permissions for DynamoDB and SNS.
