from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash

import os
import uuid
from datetime import date

app = Flask(__name__)
app.secret_key = 'admin'

import os

DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///golf_tournament.db')
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# =======================================
# SQLAlchemy Models (Tables)
# =======================================

class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player1 = db.Column(db.String, nullable=False)
    player2 = db.Column(db.String, nullable=False)
    handicap1 = db.Column(db.Float, nullable=False)
    handicap2 = db.Column(db.Float, nullable=False)
    avg_handicap = db.Column(db.Float, nullable=False)
    stableford_points = db.Column(db.Integer, default=0)


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    location = db.Column(db.String, nullable=False)
    par = db.Column(db.Integer, nullable=False)


class Tee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    gender = db.Column(db.String, nullable=False)
    tee_color = db.Column(db.String, nullable=False)
    course_rating = db.Column(db.Float, nullable=False)
    slope_rating = db.Column(db.Integer, nullable=False)


class Hole(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    hole_number = db.Column(db.Integer, nullable=False)
    par = db.Column(db.Integer, nullable=False)
    handicap_index = db.Column(db.Integer, nullable=False)


class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    date_played = db.Column(db.Date, nullable=False)
    hole_number = db.Column(db.Integer, nullable=False)
    strokes = db.Column(db.Integer, nullable=False)
    net_score = db.Column(db.Integer, nullable=False)
    stableford_points = db.Column(db.Integer, nullable=False)
    round_id = db.Column(db.String, nullable=False)


class PersonalScore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    date_played = db.Column(db.Date, nullable=False)
    hole_number = db.Column(db.Integer, nullable=False)
    strokes = db.Column(db.Integer, nullable=False)
    stableford_points = db.Column(db.Integer, nullable=False)
    round_id = db.Column(db.String, nullable=False)
    playing_handicap = db.Column(db.Integer, nullable=False)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    home_club = db.Column(db.String, nullable=False)
    birthdate = db.Column(db.Date, nullable=False)
    username = db.Column(db.String, unique=True, nullable=False)
    email = db.Column(db.String, unique=True, nullable=False)
    password_hash = db.Column(db.String, nullable=False)


class CourseDetail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    hole_number = db.Column(db.Integer, nullable=False)
    par = db.Column(db.Integer, nullable=False)
    strokes_given = db.Column(db.Integer, nullable=False)

# =======================================
# Initialize DB Tables
# =======================================

def init_db():
    print("⚙️ [INIT] Attempting to initialize database...")
    try:
        db.create_all()
        print("✅ [INIT] Database tables created successfully.")
    except Exception as e:
        print(f"❌ [INIT] Database initialization error: {e}")

def calculate_stableford(par, net_score):
    score_diff = net_score - par
    if score_diff <= -3:
        return 5 # Double Eagle
    elif score_diff == -2:
        return 4  # Eagle 
    elif score_diff == -1:
        return 3  # Birdie
    elif score_diff == 0:
        return 2  # Par
    elif score_diff == 1:
        return 1  # Bogey
    else:
        return 0  # Worse than Double Bogey
    
def calculate_playing_handicap(avg_handicap, course_rating, slope_rating, course_par):
    return round((avg_handicap * (slope_rating / 113)) + (course_rating - course_par))

def update_handicap(team_id, score):
    team = Team.query.get(team_id)
    if team:
        new_handicap1 = max(0, team.handicap1 - (score * 0.1))
        new_handicap2 = max(0, team.handicap2 - (score * 0.1))
        team.handicap1 = new_handicap1
        team.handicap2 = new_handicap2
        team.avg_handicap = (new_handicap1 + new_handicap2) / 2
        db.session.commit()

@app.route('/')
def main():
    return render_template('main.html')

#------------------------------------------------------------------------------------------
#Register a user
@app.route('/register_user', methods=['GET', 'POST'])
def register_user():
    if request.method == 'POST':
        name = request.form.get('name')
        home_club = request.form.get('home_club')
        birthdate = request.form.get('birthdate')
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        password_hash = generate_password_hash(password)

        try:
            user = User(name=name, home_club=home_club, birthdate=birthdate,
                        username=username, email=email, password_hash=password_hash)
            db.session.add(user)
            db.session.commit()

            # Auto login
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('user_rounds'))

        except:
            db.session.rollback()
            return "Username or Email already exists. Please choose another."

    return render_template('register_user.html')

#------------------------------------------------------------------------------------------
#Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('user_rounds'))
        else:
            return render_template('login.html', error='Invalid credentials')

    return render_template('login.html')

#------------------------------------------------------------------------------------------
#Logout
@app.route('/logout')
def logout():
    session.clear()  # Clear session data
    return redirect(url_for('main'))  # Redirect to main page after logout

#------------------------------------------------------------------------------------------
#transfer to tournament page
@app.route('/tournament')
def tournament():
    teams = Team.query.all()
    team_results = []

    for team in teams:
        # Aggregate best 3 rounds
        best_3_scores = (
            db.session.query(db.func.sum(Score.stableford_points).label('total_points'))
            .filter(Score.team_id == team.id)
            .group_by(Score.round_id)
            .order_by(db.desc('total_points'))
            .limit(3)
            .all()
        )
        total_best_points = sum([score.total_points for score in best_3_scores if score.total_points is not None])
        team_results.append((team.id, f"{team.player1} & {team.player2}", team.avg_handicap, total_best_points))

    # Sort teams by best scores descending
    team_results.sort(key=lambda x: x[3], reverse=True)

    return render_template('tournament.html', teams=team_results)


#------------------------------------------------------------------------------------------
#team rounds view
@app.route('/team_rounds/<team_id>')
def team_rounds(team_id):
    # ✅ Fetch list of rounds played by a team
    team_rounds = (
        db.session.query(
            Score.date_played,
            Course.name,
            func.sum(Score.stableford_points),
            Score.round_id
        )
        .join(Course, Score.course_id == Course.id)
        .filter(Score.team_id == team_id)
        .group_by(Score.round_id, Score.date_played, Course.name)  # ✅ Fix here
        .order_by(Score.date_played.desc())
        .all()
    )

    return render_template('team_rounds.html', rounds=team_rounds, team_id=team_id)

#------------------------------------------------------------------------------------------
#edit team round
@app.route('/edit_team_round/<round_id>', methods=['GET', 'POST'])
def edit_team_round(round_id):
    if request.method == 'POST':
        date_played = request.form.get('date_played')

        # Fetch team_id and course_id
        score_sample = Score.query.filter_by(round_id=round_id).first()
        team_id = score_sample.team_id
        course_id = score_sample.course_id

        # Fetch avg handicap for team
        team = Team.query.get(team_id)
        team_handicap = team.avg_handicap

        # Fetch course ratings
        tee = Tee.query.filter_by(course_id=course_id).first()
        playing_handicap = calculate_playing_handicap(team_handicap, tee.course_rating, tee.slope_rating, tee.par)

        # Calculate strokes_given
        holes_data = Hole.query.filter_by(course_id=course_id).order_by(Hole.hole_number).all()
        extra_strokes = playing_handicap % 18
        base_strokes = playing_handicap // 18
        strokes_given_dict = {
            hole.hole_number: (base_strokes + (1 if hole.handicap_index <= extra_strokes else 0), hole.par)
            for hole in holes_data
        }

        # Update scores
        for i in range(1, 19):
            strokes = int(request.form.get(f'strokes_{i}', 0))
            strokes_given, par = strokes_given_dict[i]
            net_score = strokes - strokes_given
            stableford_points = calculate_stableford(par, net_score)

            score_record = Score.query.filter_by(round_id=round_id, hole_number=i).first()
            if score_record:
                score_record.strokes = strokes
                score_record.stableford_points = stableford_points

        # Update date played
        Score.query.filter_by(round_id=round_id).update({"date_played": date_played})
        db.session.commit()

        return redirect(url_for('team_rounds', team_id=team_id))
    
    # GET method
        score_sample = Score.query.filter_by(round_id=round_id).first()
    team_id = score_sample.team_id
    course_id = score_sample.course_id
    team = Team.query.get(team_id)
    team_handicap = team.avg_handicap
    tee = Tee.query.filter_by(course_id=course_id).first()
    playing_handicap = calculate_playing_handicap(team_handicap, tee.course_rating, tee.slope_rating, tee.par)

    holes_data = Hole.query.filter_by(course_id=course_id).order_by(Hole.hole_number).all()
    extra_strokes = playing_handicap % 18
    base_strokes = playing_handicap // 18

    holes = []
    for hole in holes_data:
        strokes_given = base_strokes + (1 if hole.handicap_index <= extra_strokes else 0)
        score = Score.query.filter_by(round_id=round_id, hole_number=hole.hole_number).first()
        strokes = score.strokes
        stableford_points = score.stableford_points
        holes.append((hole.hole_number, strokes, hole.par, strokes_given, stableford_points))

    return render_template('edit_team_round.html', team_id=team_id, round_id=round_id, holes=holes,
                           playing_handicap=playing_handicap, date_played=score_sample.date_played)
    
#------------------------------------------------------------------------------------------
#delete team round
@app.route('/delete_team_round/<round_id>', methods=['POST'])
def delete_team_round(round_id):
    # Query all scores associated with the given round_id
    scores_to_delete = Score.query.filter_by(round_id=round_id).all()

    # Delete all those records
    for score in scores_to_delete:
        db.session.delete(score)

    db.session.commit()  # Save changes

    return redirect(url_for('tournament'))  # Redirect to tournament page

#------------------------------------------------------------------------------------------
#team round details view
@app.route('/team_round_detail/<round_id>')
def team_round_detail(round_id):
    # ✅ Fetch team name, course name, and date played (LIMIT 1 equivalent)
    score_sample = (
        db.session.query(Score, Team, Course)
        .join(Team, Score.team_id == Team.id)
        .join(Course, Score.course_id == Course.id)
        .filter(Score.round_id == round_id)
        .first()
    )

    if not score_sample:
        return "Round not found", 404

    team = score_sample[1]
    course = score_sample[2]
    date_played = score_sample[0].date_played

    # Assemble team name and course name
    round_info = (f"{team.player1} & {team.player2}", course.name, date_played)

    # ✅ Fetch hole number, strokes, stableford points, and par
    holes_data = (
        db.session.query(Score.hole_number, Score.strokes, Score.stableford_points, Hole.par)
        .join(Hole, (Score.course_id == Hole.course_id) & (Score.hole_number == Hole.hole_number))
        .filter(Score.round_id == round_id)
        .order_by(Score.hole_number.asc())
        .all()
    )

    # ✅ Calculate totals
    total_strokes = sum([h[1] for h in holes_data])
    total_points = sum([h[2] for h in holes_data])

    return render_template(
        'team_round_detail.html',
        round_info=round_info,
        holes=holes_data,
        total_strokes=total_strokes,
        total_stableford=total_points,
        round_id=round_id,
        team_id=round_id  # Enables back button to team rounds
    )

#------------------------------------------------------------------------------------------
#Register a team
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        player1 = request.form.get('player1', '').strip()
        player2 = request.form.get('player2', '').strip()
        handicap1 = request.form.get('handicap1')
        handicap2 = request.form.get('handicap2')

        # ✅ Validate input
        if not player1 or not player2 or not handicap1 or not handicap2:
            return "Error: All fields are required!", 400

        # ✅ Convert handicaps safely
        try:
            handicap1 = float(handicap1) if handicap1 else 0.0
            handicap2 = float(handicap2) if handicap2 else 0.0
            avg_handicap = (handicap1 + handicap2) / 2
        except ValueError:
            return "Error: Invalid handicap values!", 400

        # ✅ Check if the team already exists
        existing_team = Team.query.filter_by(player1=player1, player2=player2).first()
        if existing_team:
            return "Error: This team already exists!", 400

        # ✅ Insert using SQLAlchemy
        try:
            new_team = Team(
                player1=player1,
                player2=player2,
                handicap1=handicap1,
                handicap2=handicap2,
                avg_handicap=avg_handicap
            )
            db.session.add(new_team)
            db.session.commit()
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            print(f"❌ Database error: {e}")
            return f"Error: {str(e)}", 500

    return render_template('register.html')

#------------------------------------------------------------------------------------------
#Update a score
@app.route('/update_score', methods=['POST'])
def update_score():
    team_id = request.form.get('team_id', '').strip()
    stableford_points = request.form.get('stableford_points', '').strip()

    # ✅ Input validation
    if not team_id or not stableford_points:
        return redirect(url_for('index'))

    try:
        stableford_points = int(stableford_points)
    except ValueError:
        return redirect(url_for('index'))

    # ✅ SQLAlchemy update logic
    try:
        team = Team.query.get(team_id)  # Fetch team by ID
        if team:
            team.stableford_points = stableford_points  # Update points
            db.session.commit()  # Save changes
        else:
            print(f"Team with ID {team_id} not found.")
            return redirect(url_for('index'))
    except Exception as e:
        db.session.rollback()  # Rollback in case of error
        print(f"Database error: {e}")
        return redirect(url_for('index'))

    return redirect(url_for('index'))  # Redirect after success


#------------------------------------------------------------------------------------------
#Record a score
@app.route('/record_score', methods=['GET', 'POST'])
def record_score():
    # ✅ Fetch courses and teams using SQLAlchemy
    courses = Course.query.with_entities(Course.id, Course.name).all()
    teams = Team.query.with_entities(Team.id, Team.player1, Team.player2, Team.avg_handicap).all()

    # Defaults for form fields
    selected_course = request.form.get('course_id', '')
    selected_team = request.form.get('team_id', '')
    selected_gender = request.form.get('gender', 'Men')
    selected_tee = request.form.get('tee_color', 'White')
    holes = []
    team_handicap = None
    playing_handicap = None

    # Only calculate if form submitted and required fields are filled
    if request.method == 'POST' and selected_course and selected_team:
        # ✅ Fetch tees + ratings via SQLAlchemy
        tee = (
            db.session.query(Tee.course_rating, Tee.slope_rating, Course.par)
            .join(Course, Tee.course_id == Course.id)
            .filter(Tee.course_id == selected_course, Tee.gender == selected_gender, Tee.tee_color == selected_tee)
            .first()
        )

        # ✅ Fetch team handicap via SQLAlchemy
        team = Team.query.with_entities(Team.avg_handicap).filter_by(id=selected_team).first()

        if tee and team:
            course_rating, slope_rating, course_par = tee
            team_handicap = team.avg_handicap

            # ✅ Playing Handicap calculation (same logic)
            playing_handicap = round((team_handicap * (slope_rating / 113)) + (course_rating - course_par))

            # ✅ Fetch holes via SQLAlchemy
            holes_data = (
                Hole.query
                .with_entities(Hole.hole_number, Hole.par, Hole.handicap_index)
                .filter_by(course_id=selected_course)
                .order_by(Hole.hole_number.asc())
                .all()
            )

            # ✅ Calculate strokes given
            extra_strokes = playing_handicap % 18
            base_strokes = playing_handicap // 18
            holes = []
            for hole in holes_data:
                hole_number, par, handicap_index = hole
                strokes_given = base_strokes + (1 if handicap_index <= extra_strokes else 0)
                holes.append((hole_number, par, strokes_given))

    # ✅ Render the form and results
    return render_template(
        'record_score.html',
        courses=courses,
        teams=teams,
        selected_course=selected_course,
        selected_team=selected_team,
        selected_gender=selected_gender,
        selected_tee=selected_tee,
        holes=holes,
        team_handicap=team_handicap,
        playing_handicap=playing_handicap
    )

#------------------------------------------------------------------------------------------
#Submit a score
@app.route('/submit_scores', methods=['POST'])
def submit_scores():
    team_id = request.form.get('team_id')
    course_id = request.form.get('course_id')
    date_played = request.form.get('date_played')
    round_id = str(uuid.uuid4())  # ✅ Unique round ID

    total_stableford_points = 0
    scores_to_insert = []

    # Loop through holes 1 to 18
    for i in range(1, 19):
        strokes = int(request.form.get(f'strokes_{i}', 0))
        stableford_points = int(request.form.get(f'stableford_points_{i}', 0))
        par = int(request.form.get(f'par_{i}', 0))  # For possible validation/logging
        strokes_given = int(request.form.get(f'strokes_given_{i}', 0))

        net_strokes = strokes - strokes_given  # Optional, can be stored

        total_stableford_points += stableford_points

        # Prepare Score ORM object for bulk insert
        score_entry = Score(
            team_id=team_id,
            course_id=course_id,
            date_played=date_played,
            hole_number=i,
            strokes=strokes,
            net_score=net_strokes,
            stableford_points=stableford_points,
            round_id=round_id
        )
        scores_to_insert.append(score_entry)

    # ✅ Insert all scores and update team total Stableford points
    try:
        db.session.bulk_save_objects(scores_to_insert)  # Bulk insert all hole scores
        team = Team.query.get(team_id)  # Fetch team
        if team:
            team.stableford_points += total_stableford_points  # Update total points
            db.session.commit()  # Save all changes
        else:
            print(f"Team with ID {team_id} not found.")
            db.session.rollback()
    except Exception as e:
        print(f"Database error during score submission: {e}")
        db.session.rollback()

    # ✅ Redirect to tournament or any page
    return redirect(url_for('tournament'))

#------------------------------------------------------------------------------------------
#Add a course
@app.route('/add_course', methods=['GET', 'POST'])
def add_course():
    if request.method == 'POST':
        try:
            course_name = request.form.get('course_name', '').strip()
            location = request.form.get('location', '').strip()
            par = int(request.form.get('par', 0))  # Default to 0 if missing

            if not course_name or not location:
                return "Error: Course name and location are required!", 400  # Prevent empty values

            # Check if course already exists
            existing_course = Course.query.filter_by(name=course_name).first()
            if existing_course:
                return "Error: Course with this name already exists!", 400

            # ✅ Create and add course
            new_course = Course(name=course_name, location=location, par=par)
            db.session.add(new_course)
            db.session.commit()  # Commit first to get course_id
            course_id = new_course.id

            if not course_id:
                return "Error: Course ID not found after commit", 500

            # ✅ Insert tees
            tee_colors = ['White', 'Yellow', 'Blue', 'Red', 'Orange', 'Black', 'Gold']
            genders = ['Men', 'Women']
            for gender in genders:
                for tee in tee_colors:
                    # Safely get input or use default
                    try:
                        course_rating = float(request.form.get(f'course_rating_{gender}_{tee}', '0') or 0.0)
                        slope_rating = int(request.form.get(f'slope_rating_{gender}_{tee}', '0') or 0)
                    except ValueError:
                        course_rating, slope_rating = 0.0, 0

                    new_tee = Tee(
                        course_id=course_id,
                        gender=gender,
                        tee_color=tee,
                        course_rating=course_rating,
                        slope_rating=slope_rating
                    )
                    db.session.add(new_tee)

            # ✅ Insert holes
            for hole_number in range(1, 19):
                par_value = int(request.form.get(f'par_{hole_number}', 3) or 3)  # Default Par 3
                handicap_index = int(request.form.get(f'handicap_index_{hole_number}', 18) or 18)  # Default 18

                new_hole = Hole(
                    course_id=course_id,
                    hole_number=hole_number,
                    par=par_value,
                    handicap_index=handicap_index
                )
                db.session.add(new_hole)

            # ✅ Final commit for tees and holes
            db.session.commit()
            return redirect(url_for('index'))

        except Exception as e:
            db.session.rollback()  # Rollback on error
            print(f"❌ Database error: {e}")  # Log error in console
            return f"Error: {str(e)}", 500  # Return error message instead of generic redirect

    return render_template('add_course.html')

#------------------------------------------------------------------------------------------
#List all courses

@app.route('/courses')
def courses():
    # ✅ Fetch all courses using SQLAlchemy ORM
    courses = Course.query.all()

    # ✅ Render template and pass courses
    return render_template('courses.html', courses=courses)

#------------------------------------------------------------------------------------------
#Delete a course
@app.route('/delete_course/<int:course_id>', methods=['POST'])
def delete_course(course_id):
    try:
        course = Course.query.get(course_id)

        if not course:
            print(f"❌ Course ID {course_id} not found.")
            return "Error: Course not found!", 404

        # ✅ Check if cascading deletion is handled by DB or needs manual deletion
        Tee.query.filter_by(course_id=course_id).delete()
        Hole.query.filter_by(course_id=course_id).delete()

        # ✅ Delete the course
        db.session.delete(course)
        db.session.commit()  # ✅ Commit all deletions

        print(f"✅ Successfully deleted course ID {course_id}.")
        return redirect(url_for('courses'))

    except Exception as e:
        db.session.rollback()  # Rollback on error
        print(f"❌ Database error during course deletion: {e}")
        return "Error deleting course", 500

#------------------------------------------------------------------------------------------
@app.route('/edit_course', methods=['GET', 'POST'])
def edit_course():
    courses = Course.query.all()  # Fetch all available courses

    # Get selected course ID from dropdown
    course_id = request.args.get('course_id', type=int)  # Get from query string
    course = Course.query.get(course_id) if course_id else None  # Fetch the course if selected

    if request.method == 'POST' and course:
        try:
            course.name = request.form.get('course_name').strip()
            course.location = request.form.get('location').strip()
            course.par = int(request.form.get('par'))

            db.session.commit()
            return redirect(url_for('courses'))  # Redirect after update
        except Exception as e:
            db.session.rollback()
            print(f"❌ Database error during course update: {e}")
            return f"Error updating course: {e}", 500

    return render_template('edit_course.html', courses=courses, course=course)
#------------------------------------------------------------------------------------------
#Add a personal score
@app.route('/personal_score', methods=['GET', 'POST'])
def personal_score():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    # ✅ Fetch courses using SQLAlchemy
    courses = Course.query.with_entities(Course.id, Course.name).all()

    # Collect form data
    selected_course = request.form.get('course_id', '')
    selected_gender = request.form.get('gender', 'Men')
    selected_tee = request.form.get('tee_color', 'White')
    user_handicap = request.form.get('handicap', '')
    date_played = request.form.get('date_played', '')
    holes = []
    playing_handicap = None

    # Debug logging
    print("\n[DEBUG] --- Form Data ---")
    print(f"Course ID: {selected_course}")
    print(f"Gender: {selected_gender}")
    print(f"Tee Color: {selected_tee}")
    print(f"Handicap: {user_handicap}")
    print(f"Date Played: {date_played}")

    if request.method == 'POST':
        if not selected_course or not user_handicap:
            print("[ERROR] Missing course or handicap!")
        else:
            try:
                user_handicap = float(user_handicap)
                print(f"[DEBUG] Parsed Handicap: {user_handicap}")
            except ValueError:
                print("[ERROR] Invalid handicap entered.")
                return redirect(url_for('personal_score'))

            # ✅ Fetch tee data using SQLAlchemy
            tee_data = (
                db.session.query(Tee.course_rating, Tee.slope_rating, Course.par)
                .join(Course, Tee.course_id == Course.id)
                .filter(
                    Tee.course_id == selected_course,
                    Tee.gender == selected_gender,
                    Tee.tee_color == selected_tee
                ).first()
            )

            if not tee_data:
                print("[ERROR] No matching tee data found!")
            else:
                course_rating, slope_rating, course_par = tee_data
                print(f"[DEBUG] Tee Data - Rating: {course_rating}, Slope: {slope_rating}, Par: {course_par}")

                # ✅ Calculate playing handicap
                playing_handicap = round((user_handicap * (slope_rating / 113)) + (course_rating - course_par))
                print(f"[DEBUG] Playing Handicap: {playing_handicap}")

                # ✅ Fetch hole data using SQLAlchemy
                holes_data = (
                    Hole.query
                    .with_entities(Hole.hole_number, Hole.par, Hole.handicap_index)
                    .filter_by(course_id=selected_course)
                    .order_by(Hole.hole_number.asc())
                    .all()
                )

                print(f"[DEBUG] Holes Data: {holes_data}")

                if holes_data:
                    # ✅ Calculate strokes given
                    extra_strokes = playing_handicap % 18
                    base_strokes = playing_handicap // 18

                    for hole in holes_data:
                        hole_number, par, handicap_index = hole
                        strokes_given = base_strokes + (1 if handicap_index <= extra_strokes else 0)
                        holes.append((hole_number, par, strokes_given))

                    print(f"[DEBUG] Final Holes with Strokes: {holes}")
                else:
                    print("[ERROR] No holes found for this course!")

    print("[DEBUG] --- Rendering Template ---")
    return render_template('personal_score.html',
                           courses=courses,
                           selected_course=selected_course,
                           selected_gender=selected_gender,
                           selected_tee=selected_tee,
                           user_handicap=user_handicap,
                           playing_handicap=playing_handicap,
                           holes=holes,
                           date_played=date_played)

#------------------------------------------------------------------------------------------
#Submit a personal score
@app.route('/submit_personal_score', methods=['POST'])
def submit_personal_score():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # ✅ Ensure user is logged in

    user_id = session['user_id']  # Logged-in user ID
    course_id = request.form.get('course_id')
    date_played = request.form.get('date_played')
    playing_handicap = request.form.get('playing_handicap')

    # Safeguard for playing_handicap
    playing_handicap = int(playing_handicap) if playing_handicap else 0

    # ✅ Generate unique round ID
    round_id = str(uuid.uuid4())

    scores_to_insert = []

    # ✅ Loop over holes 1 to 18 and collect scores
    for i in range(1, 19):
        try:
            strokes = int(request.form.get(f'strokes_{i}', 0))  # Safe parsing
        except (TypeError, ValueError):
            strokes = 0

        try:
            stableford_points = int(request.form.get(f'stableford_points_{i}', 0))  # Safe parsing
        except (TypeError, ValueError):
            stableford_points = 0

        # ✅ Create PersonalScore ORM object
        score_entry = PersonalScore(
            user_id=user_id,
            course_id=course_id,
            date_played=date_played,
            hole_number=i,
            strokes=strokes,
            stableford_points=stableford_points,
            round_id=round_id,
            playing_handicap=playing_handicap
        )
        scores_to_insert.append(score_entry)

    # ✅ Insert all scores in bulk
    try:
        db.session.bulk_save_objects(scores_to_insert)
        db.session.commit()  # Save all to DB
        print(f"[INFO] Round {round_id} successfully saved for user {user_id}")
    except Exception as e:
        db.session.rollback()  # Rollback in case of error
        print(f"[ERROR] Failed to save personal scores: {e}")

    # ✅ Redirect to user's rounds
    return redirect(url_for('user_rounds'))

#------------------------------------------------------------------------------------------
#user rounds view
@app.route('/user_rounds')
def user_rounds():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # ✅ Ensure user is logged in

    user_id = session['user_id']
    username = session['username']

    # ✅ Fetch rounds with total points and course name using SQLAlchemy ORM (Postgres compliant)
    rounds = (
        db.session.query(
            PersonalScore.date_played,
            Course.name.label('course_name'),
            db.func.sum(PersonalScore.stableford_points).label('total_points'),
            PersonalScore.round_id
        )
        .join(Course, PersonalScore.course_id == Course.id)
        .filter(PersonalScore.user_id == user_id)
        .group_by(
            PersonalScore.round_id,      # Group by round_id (needed)
            PersonalScore.date_played,   # Also needed since selected
            Course.name                 # Also needed since selected
        )
        .order_by(PersonalScore.date_played.desc())  # Order after grouping
        .all()
    )

    # ✅ Render template with user's rounds
    return render_template('user_rounds.html', username=username, rounds=rounds)

#------------------------------------------------------------------------------------------
# Route to display round detail
@app.route('/round_detail/<round_id>')  # UUID as string
def round_detail(round_id):
    # ✅ Fetch player name, course name, and date played
    round_info_query = (
        db.session.query(
            User.name,
            Course.name,
            PersonalScore.date_played
        )
        .join(User, PersonalScore.user_id == User.id)
        .join(Course, PersonalScore.course_id == Course.id)
        .filter(PersonalScore.round_id == round_id)
        .first()
    )

    if not round_info_query:
        return "Round not found", 404  # Optional: handle case where round does not exist

    # ✅ Fetch hole details: hole number, strokes, stableford points, par
    holes_data = (
        db.session.query(
            PersonalScore.hole_number,
            PersonalScore.strokes,
            PersonalScore.stableford_points,
            Hole.par
        )
        .join(Hole, (PersonalScore.hole_number == Hole.hole_number) & (PersonalScore.course_id == Hole.course_id))
        .filter(PersonalScore.round_id == round_id)
        .order_by(PersonalScore.hole_number.asc())
        .all()
    )

    # ✅ Calculate totals
    total_strokes = sum(hole[1] for hole in holes_data) if holes_data else 0
    total_stableford = sum(hole[2] for hole in holes_data) if holes_data else 0

    # ✅ Render template with all data
    return render_template(
        'round_detail.html',
        round_info=round_info_query,
        holes=holes_data,
        total_strokes=total_strokes,
        total_stableford=total_stableford,
        round_id=round_id 
    )

#------------------------------------------------------------------------------------------
#edit personal round
@app.route('/edit_personal_round/<round_id>', methods=['GET', 'POST'])
def edit_personal_round(round_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']  # Ensure user is logged in

    # ✅ POST method: handle form submission and update scores
    if request.method == 'POST':
        date_played = request.form.get('date_played')

        # ✅ Fetch course_id and playing_handicap
        score_sample = PersonalScore.query.filter_by(round_id=round_id).first()
        if not score_sample:
            return "Round not found!", 404

        course_id = score_sample.course_id
        playing_handicap = score_sample.playing_handicap or 0  # Handle None

        # ✅ Fetch holes data
        holes_data = Hole.query.filter_by(course_id=course_id).order_by(Hole.hole_number).all()

        # Calculate strokes given per hole
        extra_strokes = playing_handicap % 18
        base_strokes = playing_handicap // 18
        strokes_given_dict = {hole.hole_number: base_strokes + (1 if hole.handicap_index <= extra_strokes else 0) for hole in holes_data}
        par_dict = {hole.hole_number: hole.par for hole in holes_data}

        # ✅ Update scores
        for i in range(1, 19):
            strokes = int(request.form.get(f'strokes_{i}', 0))
            strokes_given = strokes_given_dict.get(i, 0)
            par = par_dict.get(i, 4)  # Default par 4
            net_score = strokes - strokes_given
            score_diff = net_score - par

            # Calculate Stableford points
            if score_diff <= -4:
                stableford_points = 6
            elif score_diff == -3:
                stableford_points = 5
            elif score_diff == -2:
                stableford_points = 4
            elif score_diff == -1:
                stableford_points = 3
            elif score_diff == 0:
                stableford_points = 2
            elif score_diff == 1:
                stableford_points = 1
            else:
                stableford_points = 0

            # ✅ Update database
            score_record = PersonalScore.query.filter_by(round_id=round_id, hole_number=i).first()
            if score_record:
                score_record.strokes = strokes
                score_record.stableford_points = stableford_points

        # ✅ Update date played for all records in round
        PersonalScore.query.filter_by(round_id=round_id).update({'date_played': date_played})

        try:
            db.session.commit()
            print(f"[INFO] Round {round_id} updated successfully.")
        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] Failed to update personal round: {e}")

        return redirect(url_for('user_rounds'))

    # ✅ GET method: fetch data for form
    else:
        # Fetch round info
        score_sample = PersonalScore.query.filter_by(round_id=round_id).first()
        if not score_sample:
            return "Round not found!", 404

        course_id = score_sample.course_id
        date_played = score_sample.date_played
        playing_handicap = score_sample.playing_handicap or 0  # Handle None

        # Fetch course name
        course = Course.query.get(course_id)
        course_name = course.name if course else "Unknown Course"

        # Fetch hole scores
        hole_scores = (
            PersonalScore.query
            .with_entities(PersonalScore.hole_number, PersonalScore.strokes, PersonalScore.stableford_points)
            .filter_by(round_id=round_id)
            .order_by(PersonalScore.hole_number.asc())
            .all()
        )

        # Fetch holes data (par, index)
        holes_data = Hole.query.filter_by(course_id=course_id).order_by(Hole.hole_number).all()

        # Calculate strokes given per hole
        extra_strokes = playing_handicap % 18
        base_strokes = playing_handicap // 18
        strokes_given_dict = {hole.hole_number: base_strokes + (1 if hole.handicap_index <= extra_strokes else 0) for hole in holes_data}
        par_dict = {hole.hole_number: hole.par for hole in holes_data}

        # ✅ Combine all for rendering
        holes = []
        for hole_number, strokes, stableford_points in hole_scores:
            par = par_dict.get(hole_number, 4)  # Default par 4
            strokes_given = strokes_given_dict.get(hole_number, 0)
            holes.append((hole_number, strokes, par, strokes_given, stableford_points))

        # ✅ Render form with data
        return render_template(
            'edit_personal_round.html',
            round_id=round_id,
            user_id=user_id,
            course_name=course_name,
            date_played=date_played,
            playing_handicap=playing_handicap,
            holes=holes
        )

#------------------------------------------------------------------------------------------
#delete user round
@app.route('/delete_personal_round/<round_id>', methods=['POST'])
def delete_personal_round(round_id):
    # ✅ Fetch and delete all scores associated with the given round_id
    try:
        PersonalScore.query.filter_by(round_id=round_id).delete()
        db.session.commit()  # Save deletion
        print(f"[INFO] Successfully deleted round {round_id}.")
    except Exception as e:
        db.session.rollback()  # Rollback on error
        print(f"[ERROR] Failed to delete personal round {round_id}: {e}")

    # ✅ Redirect to user's rounds
    return redirect(url_for('user_rounds'))

#------------------------------------------------------------------------------------------
#force init db
@app.route('/force-init-db')
def force_init_db():
    try:
        db.create_all()
        return "✅ Tables created successfully!"
    except Exception as e:
        return f"❌ Error creating tables: {e}"
###########################################################################################
#Run the application


if __name__ == '__main__':
    if not os.path.exists("templates"):
        os.makedirs("templates")

    print(f"📡 [DATABASE] Using database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")

    if os.environ.get('INIT_DB') == 'true':
        print("🔨 [INIT] INIT_DB is true, initializing DB now...")
        with app.app_context():
            init_db()
    else:
        print("ℹ️ [INIT] INIT_DB not set or false, skipping DB init.")

    PORT = int(os.environ.get('PORT', 8080))
    app.run(debug=True, use_reloader=False, host='0.0.0.0', port=PORT)

import logging

logging.basicConfig(level=logging.DEBUG)

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f"Server Error: {error}")
    return "Internal Server Error", 500