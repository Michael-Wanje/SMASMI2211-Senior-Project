from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .serializers import (
    UserRegistrationSerializer, LoginSerializer, UserProfileSerializer,
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer,
    ChangePasswordSerializer
)
from .models import PasswordResetRequest, LoginAttempt
from apps.notifications.tasks import send_notification_email
import secrets
import string
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register_user(request):
    """Register a new user"""
    try:
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Create JWT tokens
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            
            # Log successful registration
            logger.info(f"New user registered: {user.email} - {user.user_type}")
            
            # Send welcome email for residents
            if user.user_type == 'resident':
                try:
                    send_mail(
                        subject='Welcome to Visitor Management System',
                        message=f'Welcome {user.get_full_name()}! Your account is pending approval.',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        fail_silently=False,
                    )
                except Exception as e:
                    logger.error(f"Failed to send welcome email: {str(e)}")
            
            return Response({
                'message': 'Registration successful',
                'user': UserProfileSerializer(user).data,
                'tokens': {
                    'access': str(access_token),
                    'refresh': str(refresh),
                }
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return Response({
            'error': 'Registration failed. Please try again.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_user(request):
    """Authenticate user and return JWT tokens"""
    try:
        serializer = LoginSerializer(data=request.data, context={'request': request})
        ip_address = get_client_ip(request)
        email = request.data.get('email', '')
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Log successful login
            LoginAttempt.objects.create(
                email=email,
                ip_address=ip_address,
                is_successful=True,
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            # Create JWT tokens
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            
            logger.info(f"Successful login: {user.email}")
            
            return Response({
                'message': 'Login successful',
                'user': UserProfileSerializer(user).data,
                'tokens': {
                    'access': str(access_token),
                    'refresh': str(refresh),
                }
            }, status=status.HTTP_200_OK)
        
        # Log failed login attempt
        LoginAttempt.objects.create(
            email=email,
            ip_address=ip_address,
            is_successful=False,
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        logger.warning(f"Failed login attempt: {email} from {ip_address}")
        
        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)
    
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return Response({
            'error': 'Login failed. Please try again.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout_user(request):
    """Logout user by blacklisting refresh token"""
    try:
        refresh_token = request.data.get('refresh_token')
        if not refresh_token:
            return Response({
                'error': 'Refresh token required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        token = RefreshToken(refresh_token)
        token.blacklist()
        
        logger.info(f"User logged out: {request.user.email}")
        
        return Response({
            'message': 'Logout successful'
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return Response({
            'error': 'Logout failed'
        }, status=status.HTTP_400_BAD_REQUEST)

class UserProfileView(generics.RetrieveUpdateAPIView):
    """Get and update user profile"""
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def request_password_reset(request):
    """Request password reset"""
    try:
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            user = User.objects.get(email=email)
            
            # Generate secure token
            token = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(64))
            
            # Create reset request
            reset_request = PasswordResetRequest.objects.create(
                user=user,
                token=token
            )
            
            # Send reset email
            try:
                reset_url = f"http://localhost:3000/reset-password/{token}"  # Adjust URL as needed
                
                send_mail(
                    subject='Password Reset Request',
                    message=f'Click the following link to reset your password: {reset_url}',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )
                
                logger.info(f"Password reset requested for: {email}")
                
                return Response({
                    'message': 'Password reset email sent'
                }, status=status.HTTP_200_OK)
            
            except Exception as e:
                logger.error(f"Failed to send password reset email: {str(e)}")
                return Response({
                    'error': 'Failed to send reset email'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        logger.error(f"Password reset request error: {str(e)}")
        return Response({
            'error': 'Password reset request failed'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def confirm_password_reset(request):
    """Confirm password reset with token"""
    try:
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            reset_request = serializer.validated_data['reset_request']
            new_password = serializer.validated_data['new_password']
            
            # Update user password
            user = reset_request.user
            user.set_password(new_password)
            user.save()
            
            # Mark reset request as used
            reset_request.is_used = True
            reset_request.save()
            
            logger.info(f"Password reset confirmed for: {user.email}")
            
            return Response({
                'message': 'Password reset successful'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        logger.error(f"Password reset confirmation error: {str(e)}")
        return Response({
            'error': 'Password reset confirmation failed'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def change_password(request):
    """Change user password"""
    try:
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            new_password = serializer.validated_data['new_password']
            
            user.set_password(new_password)
            user.save()
            
            logger.info(f"Password changed for: {user.email}")
            
            return Response({
                'message': 'Password changed successfully'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        logger.error(f"Password change error: {str(e)}")
        return Response({
            'error': 'Password change failed'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)