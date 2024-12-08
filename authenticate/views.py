from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseForbidden
from django.db import transaction
from .forms import SignUpForm
from .models import UserProfile, Course, Request, ManagerRequest, Module, EmployeeEmail, UserModuleCompletion, CourseFeedback

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
    if request.user.userprofile.role in ['admin']:
        if request.method == 'POST':
            course=Course.objects.create(
                title=request.POST['title'],
                description=request.POST['description'],
                created_by=request.user
            )

             # Get the module data from the POST request
            module_headings = request.POST.getlist('module_heading[]')
            module_descriptions = request.POST.getlist('module_description[]')

            # Create Modules for the Course
            for heading, description in zip(module_headings, module_descriptions):
                Module.objects.create(
                    course=course,
                    heading=heading,
                    description=description
                )
            
            employee_emails = request.POST.getlist('employee_emails[]')

            for email in employee_emails:
                EmployeeEmail.objects.create(
                    course=course,
                    email=email
                )

            messages.success(request, 'Course created successfully!')
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
    completed_modules = UserModuleCompletion.objects.filter(user=request.user, module__course=course, completed=True).values_list('module', flat=True)
    
    return render(request, 'authenticate/view_course_details.html', {
        'course': course,
        'completed_modules': completed_modules
    })

@login_required
def update_module_completion(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if request.method == 'POST':
        completed_modules = request.POST.getlist('modules')
        
        for module in course.modules.all():
            completion_status, created = UserModuleCompletion.objects.get_or_create(user=request.user, module=module)
            if str(module.id) in completed_modules:
                completion_status.completed = True
            else:
                completion_status.completed = False
            completion_status.save()

    return redirect('view_course_details', course_id=course.id)

@login_required
def track_progress(request):
   
    employee_emails = request.POST.getlist('employee_emails[]')
    courses = Course.objects.all()
    progress_data = []

    
    for course in courses:
        
        enrolled_users = User.objects.filter(employee_emails__email__in=employee_emails)
        course_progress = []

        for user in enrolled_users:
            total_modules = course.modules.count()
            completed_modules = UserModuleCompletion.objects.filter(user=user, module__course=course, completed=True).count()
            progress_percentage = (completed_modules / total_modules) * 100 if total_modules else 0

            course_progress.append({
                'username': user.username,
                'completed_modules': completed_modules,
                'total_modules': total_modules,
                'progress_percentage': progress_percentage
            })

        progress_data.append({
            'course': course,
            'course_progress': course_progress
        })

    return render(request, 'authenticate/track_progress.html', {
        'progress_data': progress_data
    })

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
def track_progress(request):
    if request.user.userprofile.role in ['manager', 'admin']:
        return render(request, 'authenticate/track_progress.html')
    return HttpResponseForbidden("Access Denied")

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
    return render(request, 'authenticate/employee_dashboard.html')


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
            # Extract the course name, feedback, and rating from the form
            course_name = request.POST['course_name']
            feedback = request.POST['feedback']
            rating = request.POST.get('rating')  # Get the rating value (1-5)

            # Check if rating was provided, set a default value if not (e.g., 0 or None)
            if rating:
                rating = int(rating)  # Convert to integer
            else:
                rating = None  # or set a default value if needed

            # Save the feedback, including the rating
            CourseFeedback.objects.create(
                user=request.user,
                course_name=course_name,
                feedback=feedback,
                rating=rating  # Save the rating in the model
            )

            messages.success(request, 'Feedback submitted successfully!')
            return redirect('employee_dashboard')
        else:
            messages.error(request, 'You are not authorized to submit feedback.')
            return redirect('employee_dashboard')

    return render(request, 'authenticate/submit_feedback.html')

@login_required
def view_feedback(request):
    # Get all feedback entries
    feedback_list = CourseFeedback.objects.all()

    # Process data for the graph
    course_names = list(feedback_list.values_list('course_name', flat=True))
    ratings = list(feedback_list.values_list('rating', flat=True))

    # Calculate the average rating for each course
    from collections import defaultdict
    course_ratings = defaultdict(list)

    for course, rating in zip(course_names, ratings):
        # Only add ratings that are not None
        if rating is not None:
            course_ratings[course].append(rating)

    # Calculate average ratings, ensuring no division by zero
    average_ratings = {
        course: (sum(ratings) / len(ratings)) if ratings else 0  # Default to 0 if no ratings
        for course, ratings in course_ratings.items()
    }

    # Prepare the data to pass to the template for graph
    course_labels = list(average_ratings.keys())
    average_values = list(average_ratings.values())

    return render(request, 'authenticate/view_feedback.html', {
        'feedback_list': feedback_list,
        'course_labels': course_labels,
        'average_values': average_values
    })
