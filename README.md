# Interview Preparation Platform

A comprehensive web-based platform for students to prepare for technical and non-technical interviews. The system supports multiple user roles (Student, Faculty, Admin), live coding practice, quizzes, performance analytics, company-wise interview preparation, learning resources, leaderboard, notifications, and an AI chatbot-based virtual interview system.

## 🎯 Features

### 👥 User Roles

#### Student
- Secure login & authentication
- Dashboard with coding and non-coding questions
- Live coding environment (C, C++, Python, Java)
- Auto-evaluation & result display
- Performance analysis (time, accuracy, efficiency)
- Upload learning materials (PDF, code snippets, flashcards)
- Company-wise interview question browsing
- View leaderboard
- Receive faculty feedback & notifications
- Attend chatbot-based virtual interview

#### Faculty
- Secure login
- Create & manage quizzes and assignments
- Track student performance
- View analytics and progress reports
- Provide feedback after evaluations
- Monitor overall student activity

#### Admin
- Full platform control
- Add/remove faculty
- Manage student accounts
- Review & approve questions
- Handle reported content
- Monitor platform usage and system statistics

### 🔐 Security Features
- JWT-based authentication
- Role-based access control
- Secure API routes
- Password hashing with bcrypt
- Environment variable configuration

### 💻 Core Modules

1. **Live Coding Module**
   - Embedded live compiler
   - Support for C, C++, Python, Java
   - Real-time code execution
   - Error handling and output display
   - Time tracking per submission

2. **Non-Coding Assessment Module**
   - MCQs with auto-evaluation
   - Fill-in-the-blanks
   - Instant score generation

3. **Performance & Analytics**
   - Student-wise performance tracking
   - Quiz scores and coding accuracy
   - Time analysis and efficiency calculation
   - Dashboard-friendly data visualization

4. **Company-Wise Interview Preparation**
   - Company name tagging for questions
   - Search & filter by company
   - Company-specific interview patterns

5. **Learning Resources Module**
   - Upload PDF notes, code snippets, flashcards
   - Categorization and tagging
   - Company-wise organization

6. **Leaderboard System**
   - Ranking based on quiz scores, coding performance, accuracy
   - Gamification and motivation
   - Peer competition

7. **Notification System**
   - Dashboard notifications
   - Feedback, quiz results, assignments
   - Real-time updates

8. **AI Chatbot – Virtual Interview**
   - Mock interview sessions
   - Questions based on resume and JD
   - HR and technical questions
   - Post-interview feedback

## 🛠️ Tech Stack

- **Frontend**: HTML, CSS, Vanilla JavaScript
- **Backend**: Python Flask
- **Database**: MySQL (with PyMySQL connector)
- **Authentication**: JWT (Flask-JWT-Extended)
- **Code Execution**: Online compiler API (JDoodle) or local Python execution
- **AI Chatbot**: OpenAI API (or fallback rule-based system)

## 📦 Installation & Setup

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- Modern web browser

### Backend Setup

1. **Navigate to backend directory**
   ```bash
   cd backend
   ```

2. **Create virtual environment (recommended)**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables (optional)**
   Create a `.env` file in the backend directory:
   ```env
   SECRET_KEY=your-secret-key-here
   JWT_SECRET_KEY=your-jwt-secret-key-here
   DATABASE_URL=sqlite:///interview_platform.db
   COMPILER_CLIENT_ID=your-compiler-api-id
   COMPILER_CLIENT_SECRET=your-compiler-api-secret
   AI_API_KEY=your-openai-api-key
   ```

5. **Run the Flask server**
   ```bash
   python app.py
   ```
   
   The backend will run on `http://localhost:5000`

### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd frontend
   ```

2. **Open in browser**
   - Simply open `index.html` in a modern web browser
   - Or use a local server:
     ```bash
     # Using Python
     python -m http.server 8000
     
     # Using Node.js (if installed)
     npx http-server -p 8000
     ```

3. **Access the application**
   - Open `http://localhost:8000` in your browser
   - Or directly open `index.html`

### Database Initialization

1. **Setup Database**
   ```bash
   cd backend
   python setup_database.py
   ```

2. **Run Migrations**
   ```bash
   python migrate_assessments.py
   python migrate_module_type.py
   ```

3. **Test Connection**
   ```bash
   python test_connection.py
   ```

4. **Start Server**
   ```bash
   python app.py
   ```

The database is automatically initialized when you first run the Flask app. Sample data (seed data) will be created including:
- Admin user: `admin` / `admin123`
- Faculty user: `faculty1` / `faculty123`
- Student user: `student1` / `student123`
- Sample companies (Google, Microsoft, Amazon, etc.)
- Sample coding questions
- Sample MCQ and fill-in-the-blank questions

**Database Configuration:**
- Default: MySQL on `localhost:3306`
- Database name: `cursor_platform`
- Configure in `backend/.env` file (see `.env.example`)

## 🚀 Usage

### Default Login Credentials

**Admin:**
- Username: `admin`
- Password: `admin123`

**Faculty:**
- Username: `faculty1`
- Password: `faculty123`

**Student:**
- Username: `student1`
- Password: `student123`

### Getting Started

1. **Login** with one of the default accounts or register a new account
2. **Student Dashboard**: View recent submissions, available quizzes, notifications, and performance summary
3. **Coding Practice**: Select a question, write code, run it, and submit for evaluation
4. **Quizzes**: Take quizzes with MCQ and fill-in-the-blank questions
5. **Companies**: Browse company-specific interview questions
6. **Resources**: Upload and manage learning materials
7. **Leaderboard**: View rankings and compete with peers
8. **AI Interview**: Start a virtual interview session with the chatbot

## 📁 Project Structure

```
Demo.D/
├── backend/
│   ├── app.py                 # Main Flask application
│   ├── config.py              # Configuration settings
│   ├── models.py              # Database models
│   ├── seed_data.py           # Initial seed data
│   ├── requirements.txt       # Python dependencies
│   ├── routes/
│   │   ├── auth.py            # Authentication routes
│   │   ├── student.py         # Student routes
│   │   ├── faculty.py         # Faculty routes
│   │   ├── admin.py           # Admin routes
│   │   ├── coding.py          # Coding practice routes
│   │   ├── quiz.py            # Quiz routes
│   │   ├── resources.py       # Learning resources routes
│   │   ├── leaderboard.py     # Leaderboard routes
│   │   ├── notifications.py   # Notification routes
│   │   └── chatbot.py         # AI chatbot routes
│   └── utils/
│       ├── auth.py            # Authentication utilities
│       ├── compiler.py        # Code execution utilities
│       ├── leaderboard.py     # Leaderboard calculation
│       └── chatbot.py         # AI chatbot utilities
├── frontend/
│   ├── index.html            # Main HTML file
│   ├── css/
│   │   └── style.css         # Stylesheet
│   └── js/
│       ├── api.js            # API client functions
│       └── app.js            # Main application logic
└── README.md                 # This file
```

## 🔧 API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `POST /api/auth/refresh` - Refresh access token
- `GET /api/auth/me` - Get current user info
- `POST /api/auth/logout` - Logout user

### Student
- `GET /api/student/dashboard` - Get dashboard data
- `GET /api/student/performance` - Get performance analytics
- `GET /api/student/questions` - Get questions with filters
- `GET /api/student/resources` - Get learning resources

### Coding
- `GET /api/coding/questions/<id>` - Get question details
- `POST /api/coding/execute` - Execute code
- `POST /api/coding/submit` - Submit code for evaluation
- `GET /api/coding/submissions` - Get user submissions

### Quiz
- `GET /api/quiz/list` - List available quizzes
- `GET /api/quiz/<id>` - Get quiz details
- `POST /api/quiz/<id>/attempt` - Submit quiz attempt
- `GET /api/quiz/attempts` - Get user quiz attempts

### Faculty
- `GET /api/faculty/dashboard` - Faculty dashboard
- `POST /api/faculty/quizzes` - Create quiz
- `POST /api/faculty/questions` - Create question
- `GET /api/faculty/students/performance` - Student performance
- `POST /api/faculty/feedback` - Provide feedback

### Admin
- `GET /api/admin/dashboard` - Admin dashboard
- `GET /api/admin/users` - List users
- `PUT /api/admin/users/<id>` - Update user
- `DELETE /api/admin/users/<id>` - Delete user
- `POST /api/admin/companies` - Create company
- `GET /api/admin/companies` - List companies

### Resources
- `POST /api/resources/upload` - Upload resource
- `GET /api/resources/<id>` - Get resource
- `DELETE /api/resources/<id>` - Delete resource

### Leaderboard
- `GET /api/leaderboard/top` - Get top users
- `GET /api/leaderboard/my-rank` - Get user rank

### Notifications
- `GET /api/notifications` - Get notifications
- `PUT /api/notifications/<id>/read` - Mark as read
- `PUT /api/notifications/read-all` - Mark all as read
- `GET /api/notifications/unread-count` - Get unread count

### Chatbot
- `POST /api/chatbot/start-interview` - Start interview session
- `POST /api/chatbot/answer` - Submit answer
- `GET /api/chatbot/session/<id>` - Get session details
- `POST /api/chatbot/end-interview/<id>` - End interview

## 🧪 Testing

### Manual Testing Steps

1. **Authentication**
   - Register a new user
   - Login with credentials
   - Verify JWT token is stored

2. **Student Features**
   - View dashboard
   - Attempt coding questions
   - Take quizzes
   - Upload resources
   - View leaderboard

3. **Faculty Features**
   - Create quizzes
   - Create questions
   - View student performance
   - Provide feedback

4. **Admin Features**
   - Manage users
   - Create companies
   - Approve/reject questions

## 🔒 Security Considerations

- Change default passwords in production
- Use strong SECRET_KEY and JWT_SECRET_KEY
- Enable HTTPS in production
- Implement rate limiting
- Add input validation and sanitization
- Use environment variables for sensitive data
- Regularly update dependencies

## 📝 Notes

- The code execution uses a fallback Python executor for demo purposes. For production, integrate with a proper compiler API (JDoodle, HackerEarth, etc.)
- The AI chatbot uses a fallback rule-based system. For production, integrate with OpenAI API or similar service
- Database uses SQLite by default. For production, migrate to PostgreSQL or MySQL
- File uploads are stored locally. For production, use cloud storage (AWS S3, etc.)

## 🤝 Contributing

This is a PG/Major Project submission. For improvements:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

This project is created for educational purposes as a PG/Major Project submission.

## 👨‍💻 Author

Created as a comprehensive interview preparation platform for academic submission.

## 🎓 Project Status

✅ Complete and ready for submission

---

**Note**: This is a full-stack application suitable for PG/Major Project submission. All core features are implemented and functional.

