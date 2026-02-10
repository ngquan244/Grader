/**
 * Signup Page
 * User registration form with Canvas token support
 */
import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Loader2, Mail, Lock, User, Key, AlertCircle, GraduationCap, Eye, EyeOff, CheckCircle } from 'lucide-react';
import type { AxiosError } from 'axios';
import type { ApiError } from '../api/auth';
import './Auth.css';

interface FormData {
  email: string;
  name: string;
  password: string;
  confirmPassword: string;
  canvasAccessToken: string;
}

interface FormErrors {
  email?: string;
  name?: string;
  password?: string;
  confirmPassword?: string;
  canvasAccessToken?: string;
  general?: string;
}

const SignupPage: React.FC = () => {
  const navigate = useNavigate();
  const { signup, isLoading } = useAuth();
  
  const [formData, setFormData] = useState<FormData>({
    email: '',
    name: '',
    password: '',
    confirmPassword: '',
    canvasAccessToken: '',
  });
  
  const [errors, setErrors] = useState<FormErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  /**
   * Password strength indicators
   */
  const passwordChecks = {
    length: formData.password.length >= 8,
    uppercase: /[A-Z]/.test(formData.password),
    lowercase: /[a-z]/.test(formData.password),
    number: /[0-9]/.test(formData.password),
  };

  const passwordStrength = Object.values(passwordChecks).filter(Boolean).length;

  /**
   * Validate form fields
   */
  const validate = (): boolean => {
    const newErrors: FormErrors = {};
    
    // Email validation
    if (!formData.email.trim()) {
      newErrors.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Please enter a valid email';
    }
    
    // Name validation
    if (!formData.name.trim()) {
      newErrors.name = 'Name is required';
    } else if (formData.name.trim().length < 2) {
      newErrors.name = 'Name must be at least 2 characters';
    }
    
    // Password validation
    if (!formData.password) {
      newErrors.password = 'Password is required';
    } else if (passwordStrength < 4) {
      newErrors.password = 'Password does not meet requirements';
    }
    
    // Confirm password
    if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  /**
   * Handle input changes
   */
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    // Clear error when user types
    if (errors[name as keyof FormErrors]) {
      setErrors(prev => ({ ...prev, [name]: undefined }));
    }
  };

  /**
   * Handle form submission
   */
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validate()) return;
    
    setIsSubmitting(true);
    setErrors({});
    
    try {
      await signup({
        email: formData.email.trim().toLowerCase(),
        name: formData.name.trim(),
        password: formData.password,
        canvas_access_token: formData.canvasAccessToken.trim() || undefined,
      });
      
      // Redirect to dashboard on success
      navigate('/');
    } catch (error) {
      const axiosError = error as AxiosError<ApiError>;
      const errorMessage = axiosError.response?.data?.error || 'Registration failed. Please try again.';
      setErrors({ general: errorMessage });
    } finally {
      setIsSubmitting(false);
    }
  };

  const disabled = isLoading || isSubmitting;

  return (
    <div className="auth-container">
      <div className="auth-card auth-card-wide">
        {/* Header */}
        <div className="auth-header">
          <div className="auth-logo">
            <GraduationCap size={40} />
          </div>
          <h1>Create Account</h1>
          <p>Join AI Teaching Assistant</p>
        </div>

        {/* General error */}
        {errors.general && (
          <div className="auth-error">
            <AlertCircle size={18} />
            <span>{errors.general}</span>
          </div>
        )}

        {/* Signup form */}
        <form onSubmit={handleSubmit} className="auth-form">
          {/* Email field */}
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <div className={`input-wrapper ${errors.email ? 'error' : ''}`}>
              <Mail size={18} className="input-icon" />
              <input
                id="email"
                name="email"
                type="email"
                placeholder="you@example.com"
                value={formData.email}
                onChange={handleChange}
                disabled={disabled}
                autoComplete="email"
                autoFocus
              />
            </div>
            {errors.email && <span className="field-error">{errors.email}</span>}
          </div>

          {/* Name field */}
          <div className="form-group">
            <label htmlFor="name">Full Name</label>
            <div className={`input-wrapper ${errors.name ? 'error' : ''}`}>
              <User size={18} className="input-icon" />
              <input
                id="name"
                name="name"
                type="text"
                placeholder="John Doe"
                value={formData.name}
                onChange={handleChange}
                disabled={disabled}
                autoComplete="name"
              />
            </div>
            {errors.name && <span className="field-error">{errors.name}</span>}
          </div>

          {/* Password field */}
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <div className={`input-wrapper ${errors.password ? 'error' : ''}`}>
              <Lock size={18} className="input-icon" />
              <input
                id="password"
                name="password"
                type={showPassword ? 'text' : 'password'}
                placeholder="••••••••"
                value={formData.password}
                onChange={handleChange}
                disabled={disabled}
                autoComplete="new-password"
              />
              <button
                type="button"
                className="input-action"
                onClick={() => setShowPassword(!showPassword)}
                tabIndex={-1}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
            {errors.password && <span className="field-error">{errors.password}</span>}
            
            {/* Password strength indicator */}
            {formData.password && (
              <div className="password-requirements">
                <div className={`requirement ${passwordChecks.length ? 'met' : ''}`}>
                  <CheckCircle size={14} />
                  <span>At least 8 characters</span>
                </div>
                <div className={`requirement ${passwordChecks.uppercase ? 'met' : ''}`}>
                  <CheckCircle size={14} />
                  <span>Uppercase letter</span>
                </div>
                <div className={`requirement ${passwordChecks.lowercase ? 'met' : ''}`}>
                  <CheckCircle size={14} />
                  <span>Lowercase letter</span>
                </div>
                <div className={`requirement ${passwordChecks.number ? 'met' : ''}`}>
                  <CheckCircle size={14} />
                  <span>Number</span>
                </div>
              </div>
            )}
          </div>

          {/* Confirm Password field */}
          <div className="form-group">
            <label htmlFor="confirmPassword">Confirm Password</label>
            <div className={`input-wrapper ${errors.confirmPassword ? 'error' : ''}`}>
              <Lock size={18} className="input-icon" />
              <input
                id="confirmPassword"
                name="confirmPassword"
                type={showPassword ? 'text' : 'password'}
                placeholder="••••••••"
                value={formData.confirmPassword}
                onChange={handleChange}
                disabled={disabled}
                autoComplete="new-password"
              />
            </div>
            {errors.confirmPassword && <span className="field-error">{errors.confirmPassword}</span>}
          </div>

          {/* Canvas Access Token field (optional) */}
          <div className="form-group">
            <label htmlFor="canvasAccessToken">
              Canvas Access Token
              <span className="optional-badge">Optional</span>
            </label>
            <div className={`input-wrapper ${errors.canvasAccessToken ? 'error' : ''}`}>
              <Key size={18} className="input-icon" />
              <input
                id="canvasAccessToken"
                name="canvasAccessToken"
                type="password"
                placeholder="Canvas LMS access token"
                value={formData.canvasAccessToken}
                onChange={handleChange}
                disabled={disabled}
              />
            </div>
            <span className="field-hint">
              You can add this later from your profile settings.
            </span>
          </div>

          {/* Submit button */}
          <button
            type="submit"
            className="auth-button"
            disabled={disabled}
          >
            {isSubmitting ? (
              <>
                <Loader2 size={18} className="spin" />
                Creating account...
              </>
            ) : (
              'Create Account'
            )}
          </button>
        </form>

        {/* Footer */}
        <div className="auth-footer">
          <p>
            Already have an account?{' '}
            <Link to="/login" className="auth-link">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default SignupPage;
