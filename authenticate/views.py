from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseForbidden
from django.db import transaction
from .forms import SignUpForm
from .models import UserProfile, Course, Request, ManagerRequest, Module, EmployeeEmail, CourseFeedback
from django.core.mail import send_mail
from django.conf import settings

def home(request):
    if request.user.is_authenticated:
        role = request.user.userprofile.role
        if role == 'admin':
            return redirect('admin_dashboard')
        elif role == 'manager':
            return redirect('manager_dashboard')
        elif role == 'employee':
            return redirect('employee_dashboard')
    return render(request, 'authenticate/home.html')

def login_user(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, 'Login successful!')
            return redirect('home')
        else:
            messages.error(request, 'Invalid credentials - Please try again.')
            return redirect('login')
    return render(request, 'authenticate/login.html')

def logout_user(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')

def register_user(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = form.save()
                UserProfile.objects.filter(user=user).delete()
                UserProfile.objects.create(
                    user=user,
                    role=form.cleaned_data['role']
                )
                username = form.cleaned_data['username']
                password = form.cleaned_data['password1']
                user = authenticate(username=username, password=password)
                login(request, user)
                messages.success(request, f'Welcome {username}! Your account has been created with {form.cleaned_data["role"]} role.')
                return redirect('home')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = SignUpForm()
    return render(request, 'authenticate/register.html', {'form': form})

@login_required
def profile(request):
    return render(request, 'authenticate/profile.html', {
        'user_profile': request.user.userprofile
    })

@login_required
def view_requests(request):
    context = {}
    
    if request.user.userprofile.role == 'admin':
        employee_requests = Request.objects.all().order_by('-created_at')
        manager_requests = ManagerRequest.objects.all().order_by('-created_at')
        context = {
            'requests': employee_requests,
            'manager_requests': manager_requests
        }
    elif request.user.userprofile.role == 'manager':
        employee_requests = Request.objects.filter(submitted_by=request.user).order_by('-created_at')
        context = {'requests': employee_requests}
    else:
        return HttpResponseForbidden("Access Denied")
        
    return render(request, 'authenticate/view_requests.html', context)

@login_required
def submit_request(request):
    if request.method == 'POST':
        if request.user.userprofile.role == 'manager':
            ManagerRequest.objects.create(
                manager=request.user,
                title=request.POST['title'],
                description=request.POST['description'],
                status='pending'
            )
            messages.success(request, 'Request submitted successfully!')
            return redirect('manager_dashboard')
        elif request.user.userprofile.role == 'employee':
            Request.objects.create(
                title=request.POST['title'],
                description=request.POST['description'],
                submitted_by=request.user
            )
            messages.success(request, 'Request submitted successfully!')
            return redirect('employee_dashboard')
    return render(request, 'authenticate/submit_request.html')

@login_required
def create_course(request):
    if request.user.userprofile.role in ['admin']:  # Only admins can create courses
        if request.method == 'POST':
            # Step 1: Create the course, including the deadline
            course = Course.objects.create(
                title=request.POST['title'],
                description=request.POST['description'],
                created_by=request.user,
                deadline=request.POST['deadline']  # Handle the deadline field
            )

            # Step 2: Get the module data from the POST request
            module_headings = request.POST.getlist('module_heading[]')
            module_descriptions = request.POST.getlist('module_description[]')

            # Step 3: Create Modules for the Course
            for heading, description in zip(module_headings, module_descriptions):
                Module.objects.create(
                    course=course,
                    heading=heading,
                    description=description
                )

            # Step 4: Get the list of employee emails and associate them with the course
            employee_emails = request.POST.getlist('employee_emails[]')

            for email in employee_emails:
                # Create EmployeeEmail association
                EmployeeEmail.objects.create(
                    course=course,
                    email=email
                )

            # Step 6: Display a success message and redirect
            messages.success(request, 'Course created successfully and notifications sent!')
            return redirect('admin_dashboard')

        return render(request, 'authenticate/create_course.html')

    return HttpResponseForbidden("Access Denied")
    
@login_required
def view_courses(request):
    user_email = request.user.email
    accessible_courses = Course.objects.filter(employee_emails__email=user_email).order_by('-created_at')
    if request.user.userprofile.role in ['admin', 'manager']:
        accessible_courses = Course.objects.all().order_by('-created_at')
    return render(request, 'authenticate/view_courses.html', {'courses': accessible_courses})

@login_required
def view_course_details(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    # Get the modules that are completed by the current user
    completed_modules = course.modules.filter(is_completed=True)

    return render(request, 'authenticate/view_course_details.html', {
        'course': course,
        'completed_modules': completed_modules
    })

@login_required
def mark_module_completed(request, module_id):
    module = get_object_or_404(Module, id=module_id)
    
    module.is_completed = not module.is_completed
    module.save()
    if module.is_completed:
        module.users_completed.add(request.user)  
    else:
        module.users_completed.remove(request.user)
    return redirect('view_course_details', course_id=module.course.id) 


@login_required
def track_progress(request):
    courses = Course.objects.all()  
    progress_data = []

    for course in courses:
        course_progress = []
        usernames = []
        progress_percentages = []

        for user in User.objects.all():
            if user.userprofile.role == 'employee':  
                total_modules = course.modules.count()
                completed_modules = course.modules.filter(users_completed=user)
                completed_count = completed_modules.count()

                if total_modules > 0:
                    progress_percentage = (completed_count / total_modules) * 100
                else:
                    progress_percentage = 0

                if progress_percentage > 0:
                    course_progress.append({
                        'username': user.username,
                        'completed_modules': completed_count,
                        'total_modules': total_modules,
                        'progress_percentage': progress_percentage
                    })
                    usernames.append(user.username)
                    progress_percentages.append(progress_percentage)

        if course_progress:
            progress_data.append({
                'course': course,
                'course_progress': course_progress,
                'usernames': usernames,
                'progress_percentages': progress_percentages
            })

    return render(request, 'authenticate/track_progress.html', {'progress_data': progress_data})

@login_required
def handle_request(request, request_id):
    if request.user.userprofile.role == 'admin' and request.method == 'POST':
        manager_request = ManagerRequest.objects.get(id=request_id)
        action = request.POST.get('action')
        if action in ['approved', 'rejected']:
            manager_request.status = action
            manager_request.save()
            messages.success(request, f'Request {action} successfully!')
    return redirect('view_requests')

@login_required
def delete_request(request, request_id):
    if request.user.userprofile.role == 'admin':
        req = Request.objects.get(id=request_id)
        req.delete()
        messages.success(request, 'Request deleted successfully!')
    return redirect('view_requests')

@login_required
def delete_course(request, course_id):
    if request.user.userprofile.role == 'admin':
        course = Course.objects.get(id=course_id)
        course.delete()
        messages.success(request, 'Course deleted successfully!')
    return redirect('view_courses')



@login_required
def generate_cred(request):
    if request.user.userprofile.role in ['admin']:
        return render(request, 'authenticate/generate_cred.html')
    return HttpResponseForbidden("Access Denied")

@login_required
def admin_dashboard(request):
    if request.user.userprofile.role != 'admin':
        messages.error(request, 'Access Denied: Admin privileges required')
        return redirect('home')
    return render(request, 'authenticate/admin_dashboard.html')

@login_required
def manager_dashboard(request):
    if request.user.userprofile.role != 'manager':
        messages.error(request, 'Access Denied: Manager privileges required')
        return redirect('home')
    return render(request, 'authenticate/manager_dashboard.html')

@login_required
def employee_dashboard(request):
    if request.user.userprofile.role != 'employee':
        messages.error(request, 'Access Denied: Employee privileges required')
        return redirect('home')
 
    user_email = request.user.email
    unread_notifications_count = Course.objects.filter(
        employee_emails__email=user_email,
        is_read=False
    ).count()

    return render(request, 'authenticate/employee_dashboard.html', {'unread_notifications_count': unread_notifications_count})


@login_required
def my_requests(request):
    if request.user.userprofile.role == 'employee':
        user_requests = Request.objects.filter(submitted_by=request.user).order_by('-created_at')
        return render(request, 'authenticate/my_requests.html', {'requests': user_requests})
    elif request.user.userprofile.role == 'manager':
        manager_requests = ManagerRequest.objects.filter(manager=request.user).order_by('-created_at')
        return render(request, 'authenticate/my_requests.html', {'requests': manager_requests})
    return HttpResponseForbidden("Access Denied")

@login_required
def admin_requests(request):
    if request.user.userprofile.role == 'admin':
        employee_requests = Request.objects.all().order_by('-created_at')
        manager_requests = ManagerRequest.objects.all().order_by('-created_at')
        context = {
            'employee_requests': employee_requests,
            'manager_requests': manager_requests
        }
        return render(request, 'authenticate/admin_requests.html', context)
    return HttpResponseForbidden("Access Denied")


@login_required
def view_requests(request):
    context = {}
    
    if request.user.userprofile.role == 'admin':
        # Admin sees both employee and manager requests
        employee_requests = Request.objects.all().order_by('-created_at')
        manager_requests = ManagerRequest.objects.all().order_by('-created_at')
        context = {
            'requests': employee_requests,
            'manager_requests': manager_requests
        }
    elif request.user.userprofile.role == 'manager':
        # Managers see their own requests with status
        manager_requests = ManagerRequest.objects.filter(manager=request.user).order_by('-created_at')
        context = {
            'manager_requests': manager_requests,
            'show_status': True
        }
    
    return render(request, 'authenticate/view_requests.html', context)


from django.http import JsonResponse
from rest_framework.decorators import api_view

@api_view(['GET'])
def my_progress_view(request):
    # Add your logic here to track user progress
    return JsonResponse({
        'status': 'success',
        'message': 'Progress retrieved successfully'
    })


from django.http import JsonResponse
from rest_framework.decorators import api_view


from django.shortcuts import render

def my_progress_view(request):
    context = {
        'courses_completed': 3,
        'courses_in_progress': 2,
        'total_hours': 45,
        'achievements': [
            {'name': 'Python Basics', 'completion': 100},
            {'name': 'Django Framework', 'completion': 75},
            {'name': 'REST APIs', 'completion': 60}
        ],
        'recent_activities': [
            {'course': 'Web Development', 'date': '2024-01-15'},
            {'course': 'Database Design', 'date': '2024-01-14'}
        ]
    }
    return render(request, 'authenticate/progress.html', context)


from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
import random
import string
from authenticate.models import UserProfile

@login_required
def generate_cred(request):
    if request.user.userprofile.role != 'admin':
        return HttpResponseForbidden("Access Denied")

    if request.method == 'POST':
        first_name = request.POST.get('first_name', 'Employee')
        last_name = request.POST.get('last_name', 'User')
        email = request.POST.get('email', '').strip()

        if User.objects.filter(email=email).exists():
            return JsonResponse({'error': 'Email is already taken. Please try another one.'}, status=400)


        username = f"{first_name.lower()}.{last_name.lower()}{random.randint(100, 999)}"
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))


        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
            email=email
        )

        try:
            user_profile = UserProfile.objects.get(user=user)
            
        except ObjectDoesNotExist:
           
            UserProfile.objects.create(user=user, role='employee')

       
        return JsonResponse({'username': username, 'password': password})

    return render(request, 'authenticate/generate_cred.html')


@login_required
def submit_feedback(request):
    if request.method == 'POST':
        if request.user.userprofile.role == 'employee':
            
            course_name = request.POST['course_name']
            feedback = request.POST['feedback']
            rating = request.POST.get('rating')  # Get the rating value (1-5)

            
            if rating:
                rating = int(rating)  
            else:
                rating = None  

            
            CourseFeedback.objects.create(
                user=request.user,
                course_name=course_name,
                feedback=feedback,
                rating=rating  
            )

            messages.success(request, 'Feedback submitted successfully!')
            return redirect('employee_dashboard')
        else:
            messages.error(request, 'You are not authorized to submit feedback.')
            return redirect('employee_dashboard')

    return render(request, 'authenticate/submit_feedback.html')

@login_required
def view_feedback(request):
    feedback_list = CourseFeedback.objects.all()
    
    course_names = list(feedback_list.values_list('course_name', flat=True))
    ratings = list(feedback_list.values_list('rating', flat=True))
    
    from collections import defaultdict
    course_ratings = defaultdict(list)

    for course, rating in zip(course_names, ratings):       
        if rating is not None:
            course_ratings[course].append(rating)

    average_ratings = {
        course: (sum(ratings) / len(ratings)) if ratings else 0  
        for course, ratings in course_ratings.items()
    }
    course_labels = list(average_ratings.keys())
    average_values = list(average_ratings.values())

    # Count the number of each rating (1-5 stars)
    rating_counts = {i: ratings.count(i) for i in range(1, 6)}

    return render(request, 'authenticate/view_feedback.html', {
        'feedback_list': feedback_list,
        'course_labels': course_labels,
        'average_values': average_values,
        'rating_counts': rating_counts
    })

from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Course  # Adjust this based on your actual model location

@login_required
def mark_as_read(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    # Mark the course as read
    course.is_read = True
    course.save()

    return redirect('view_notifications')


def send_course_assigned_email(course):
    # Assuming `employee_emails` is a ManyToManyField on the Course model
    # that links to a User model, and that each User has an 'email' field.
    for user in course.employee_emails.all():  # Iterate over all related users
        user_email = user.email  # Access the email of each related user

        subject = 'New Course Assigned to You'
        message = render_to_string('authenticate/course_assigned_email.html', {
            'course_title': course.title,  # Use 'title' instead of 'name'
            'course_description': course.description,  # Use 'description'
            'user_email': user_email,
        })

        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER,  # Sender email
            [user_email],  # Recipient email
            fail_silently=False,
        )

def view_notifications(request):
    user_email = request.user.email

    accessible_courses = Course.objects.filter(
        employee_emails__email=user_email,  
        is_read=False                       
    ).order_by('-created_at')  

    
    if request.user.userprofile.role in ['admin', 'manager']:
        accessible_courses = Course.objects.filter(is_read=False).order_by('-created_at')

    return render(request, 'authenticate/view_notifications.html', {'courses': accessible_courses})


@login_required
def my_progress(request):
    
    user = request.user

    
    courses = Course.objects.all()  
    progress_data = []

    for course in courses:
        # For each course, get the user's progress
        total_modules = course.modules.count()
        completed_modules = course.modules.filter(users_completed=user)
        completed_count = completed_modules.count()

        # Calculate progress percentage
        if total_modules > 0:
            progress_percentage = (completed_count / total_modules) * 100
        else:
            progress_percentage = 0

        # Add this course's progress to the progress data list
        if(progress_percentage>0):
            progress_data.append({
            'course': course,
            'completed_modules': completed_count,
            'total_modules': total_modules,
            'progress_percentage': progress_percentage
        })

    
    return render(request, 'authenticate/my_progress.html', {'progress_data': progress_data})


from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages

@login_required
def add_employee_emails(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    
    if request.user.userprofile.role in ['admin'] or request.user == course.created_by:
        if request.method == 'POST':
            
            employee_emails = request.POST.getlist('employee_emails[]')
            
            for email in employee_emails:
                EmployeeEmail.objects.create(
                    course=course,
                    email=email
                )

            messages.success(request, 'Emails added successfully!')
            return redirect('view_course_details', course_id=course.id)

    else:
        messages.error(request, "You do not have permission to add emails to this course.")
        return redirect('view_course_details', course_id=course.id)


def admin_dashboard(request):
    total_users = UserProfile.objects.count()

    total_courses = Course.objects.count()

    pending_requests = ManagerRequest.objects.filter(status='pending').count()

    context = {
        'total_users': total_users,
        'total_courses': total_courses,
        'pending_requests': pending_requests,
    }

    return render(request, 'authenticate/admin_dashboard.html', context)

def manager_dashboard(request): 
    total_courses = Course.objects.count()

    approved_requests = ManagerRequest.objects.filter(status='approved').count()

    pending_requests = ManagerRequest.objects.filter(status='pending').count()

    context = {
        'total_courses': total_courses,
        'approved_requests': approved_requests,
        'pending_requests': pending_requests,
    }

    return render(request, 'authenticate/manager_dashboard.html', context)

def employee_dashboard(request):
    user_email = request.user.email
    assigned_courses = Course.objects.filter(employee_emails__email=user_email).count()

    user = request.user
    courses_100_percent = 0
    courses_0_percent = 0
    
    courses = Course.objects.filter(employee_emails__email=user_email) 
    progress_data = []

    for course in courses:
        
        total_modules = course.modules.count()
        completed_modules = course.modules.filter(users_completed=user)
        completed_count = completed_modules.count()

        
        if total_modules > 0:
            progress_percentage = (completed_count / total_modules) * 100
        else:
            progress_percentage = 0

        if progress_percentage == 100:
            courses_100_percent += 1
        elif progress_percentage == 0:
            courses_0_percent += 1

    user_email = request.user.email
    unread_notifications_count = Course.objects.filter(
        employee_emails__email=user_email,
        is_read=False
    ).count()
        
    context = {
        'courses_assigned': assigned_courses,
        'courses_completed': courses_100_percent,
        'courses_to_start': courses_0_percent,
        'unread_notifications_count': unread_notifications_count,
    }

    return render(request, 'authenticate/employee_dashboard.html', context)
