// Global utility functions
function showMessage(message, type = 'info') {
  alert(message);
}

// ============================================
// LOGIN PAGE
// ============================================
if (document.getElementById('loginForm')) {
  document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    
    try {
      const response = await fetch('/api/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ email, password })
      });
      
      const data = await response.json();
      
      if (data.success) {
        showMessage(data.message, 'success');
        window.location.href = data.redirect;
      } else {
        showMessage(data.message, 'error');
      }
    } catch (error) {
      showMessage('Login failed: ' + error.message, 'error');
    }
  });
}

// ============================================
// SIGNUP PAGE
// ============================================
if (document.getElementById('signupForm')) {
  document.getElementById('signupForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const fullname = document.getElementById('fullname').value;
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const confirm = document.getElementById('confirm').value;
    
    if (password.length < 6) {
      showMessage('Password must be at least 6 characters long', 'error');
      return;
    }
    
    if (password !== confirm) {
      showMessage('Passwords do not match', 'error');
      return;
    }
    
    try {
      const response = await fetch('/api/signup', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ fullname, email, password })
      });
      
      const data = await response.json();
      
      if (data.success) {
        showMessage(data.message, 'success');
        setTimeout(() => {
          window.location.href = '/login';
        }, 1000);
      } else {
        showMessage(data.message, 'error');
      }
    } catch (error) {
      showMessage('Signup failed: ' + error.message, 'error');
    }
  });
}

// ============================================
// USER DASHBOARD
// ============================================
if (window.location.pathname.includes('user.html') || window.location.pathname === '/user') {
  // Load profile
  async function loadProfile() {
    try {
      const response = await fetch('/api/profile');
      const data = await response.json();
      
      if (data.success) {
        document.getElementById('username').textContent = data.user.fullname;
        document.getElementById('email').textContent = data.user.email;
        
        // Update profile picture if available
        const profilePicture = document.getElementById('profilePicture');
        if (profilePicture) {
          if (data.user.profile_picture) {
            // User has a profile picture - load it
            const imageUrl = `/static/${data.user.profile_picture}?t=${Date.now()}`;
            console.log('📸 Setting profile picture src to:', imageUrl);
            profilePicture.src = imageUrl;
            
            // Force image reload
            profilePicture.onload = () => {
              console.log('✅ Profile picture loaded successfully');
            };
            profilePicture.onerror = () => {
              console.error('❌ Profile picture failed to load:', imageUrl);
              // Fallback to default image
              profilePicture.src = 'https://i.imgur.com/6VBx3io.png';
            };
          } else {
            // No profile picture - use default
            console.log('⚠️ No profile picture found in database for user');
            profilePicture.src = 'https://i.imgur.com/6VBx3io.png';
          }
        } else {
          console.error('❌ Profile picture element not found!');
        }
      }
    } catch (error) {
      console.error('Error loading profile:', error);
    }
  }
  
  // Handle profile picture upload
  const profilePictureInput = document.getElementById('profilePictureInput');
  if (profilePictureInput) {
    profilePictureInput.addEventListener('change', async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      
      // Validate file type
      const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp'];
      if (!allowedTypes.includes(file.type)) {
        alert('Invalid file type. Please upload a PNG, JPG, JPEG, GIF, or WEBP image.');
        return;
      }
      
      // Validate file size (max 5MB)
      if (file.size > 5 * 1024 * 1024) {
        alert('File size too large. Please upload an image smaller than 5MB.');
        return;
      }
      
      const formData = new FormData();
      formData.append('profile_picture', file);
      
      const statusDiv = document.getElementById('profilePictureUploadStatus');
      if (statusDiv) {
        statusDiv.style.display = 'block';
        statusDiv.textContent = 'Uploading...';
        statusDiv.style.background = '#d1ecf1';
        statusDiv.style.color = '#0c5460';
      }
      
      try {
        const response = await fetch('/api/profile-picture', {
          method: 'POST',
          body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
          // Update profile picture
          const profilePicture = document.getElementById('profilePicture');
          if (profilePicture) {
            profilePicture.src = `/static/${data.profile_picture}?t=${Date.now()}`;
          }
          
          if (statusDiv) {
            statusDiv.textContent = 'Profile picture updated successfully!';
            statusDiv.style.background = '#d4edda';
            statusDiv.style.color = '#155724';
            setTimeout(() => {
              statusDiv.style.display = 'none';
            }, 3000);
          }
        } else {
          if (statusDiv) {
            statusDiv.textContent = `Error: ${data.message}`;
            statusDiv.style.background = '#f8d7da';
            statusDiv.style.color = '#721c24';
          }
        }
      } catch (error) {
        console.error('Error uploading profile picture:', error);
        if (statusDiv) {
          statusDiv.textContent = 'Error uploading profile picture. Please try again.';
          statusDiv.style.background = '#f8d7da';
          statusDiv.style.color = '#721c24';
        }
      }
      
      // Reset input
      e.target.value = '';
    });
  }
  
  // Edit profile
  if (document.getElementById('editProfileBtn')) {
    document.getElementById('editProfileBtn').addEventListener('click', () => {
      document.getElementById('editProfileForm').style.display = 'block';
      document.getElementById('newUsername').value = document.getElementById('username').textContent;
      document.getElementById('newEmail').value = document.getElementById('email').textContent;
    });
  }
  
  if (document.getElementById('saveProfileBtn')) {
    document.getElementById('saveProfileBtn').addEventListener('click', async () => {
      const fullname = document.getElementById('newUsername').value;
      const email = document.getElementById('newEmail').value;
      
      try {
        const response = await fetch('/api/profile', {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ fullname, email })
        });
        
        const data = await response.json();
        
        if (data.success) {
          showMessage(data.message, 'success');
          document.getElementById('username').textContent = fullname;
          document.getElementById('email').textContent = email;
          document.getElementById('editProfileForm').style.display = 'none';
        }
      } catch (error) {
        showMessage('Update failed: ' + error.message, 'error');
      }
    });
  }
  
  if (document.getElementById('cancelEditBtn')) {
    document.getElementById('cancelEditBtn').addEventListener('click', () => {
      document.getElementById('editProfileForm').style.display = 'none';
    });
  }
  
  // Change password
  if (document.getElementById('changePasswordBtn')) {
    document.getElementById('changePasswordBtn').addEventListener('click', () => {
      const form = document.getElementById('changePasswordForm');
      form.style.display = form.style.display === 'none' ? 'block' : 'none';
      if (form.style.display === 'block') {
        document.getElementById('currentPassword').value = '';
        document.getElementById('newPassword').value = '';
        document.getElementById('confirmPassword').value = '';
        document.getElementById('passwordMessage').style.display = 'none';
      }
    });
  }
  
  if (document.getElementById('cancelPasswordBtn')) {
    document.getElementById('cancelPasswordBtn').addEventListener('click', () => {
      document.getElementById('changePasswordForm').style.display = 'none';
      document.getElementById('currentPassword').value = '';
      document.getElementById('newPassword').value = '';
      document.getElementById('confirmPassword').value = '';
      document.getElementById('passwordMessage').style.display = 'none';
    });
  }
  
  if (document.getElementById('savePasswordBtn')) {
    document.getElementById('savePasswordBtn').addEventListener('click', async () => {
      const currentPassword = document.getElementById('currentPassword').value;
      const newPassword = document.getElementById('newPassword').value;
      const confirmPassword = document.getElementById('confirmPassword').value;
      const messageDiv = document.getElementById('passwordMessage');
      
      if (!currentPassword || !newPassword || !confirmPassword) {
        messageDiv.style.display = 'block';
        messageDiv.style.cssText = 'display: block; margin-top: 10px; padding: 10px; border-radius: 5px; background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb;';
        messageDiv.textContent = 'All fields are required';
        return;
      }
      
      if (newPassword !== confirmPassword) {
        messageDiv.style.display = 'block';
        messageDiv.style.cssText = 'display: block; margin-top: 10px; padding: 10px; border-radius: 5px; background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb;';
        messageDiv.textContent = 'New passwords do not match';
        return;
      }
      
      if (newPassword.length < 6) {
        messageDiv.style.display = 'block';
        messageDiv.style.cssText = 'display: block; margin-top: 10px; padding: 10px; border-radius: 5px; background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb;';
        messageDiv.textContent = 'Password must be at least 6 characters long';
        return;
      }
      
      try {
        const response = await fetch('/api/change-password', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            current_password: currentPassword,
            new_password: newPassword,
            confirm_password: confirmPassword
          })
        });
        
        const data = await response.json();
        
        messageDiv.style.display = 'block';
        
        if (data.success) {
          messageDiv.style.cssText = 'display: block; margin-top: 10px; padding: 10px; border-radius: 5px; background: #d4edda; color: #155724; border: 1px solid #c3e6cb;';
          messageDiv.textContent = data.message;
          document.getElementById('currentPassword').value = '';
          document.getElementById('newPassword').value = '';
          document.getElementById('confirmPassword').value = '';
          setTimeout(() => {
            document.getElementById('changePasswordForm').style.display = 'none';
            messageDiv.style.display = 'none';
          }, 2000);
        } else {
          messageDiv.style.cssText = 'display: block; margin-top: 10px; padding: 10px; border-radius: 5px; background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb;';
          messageDiv.textContent = data.message || 'Failed to change password';
        }
      } catch (error) {
        messageDiv.style.display = 'block';
        messageDiv.style.cssText = 'display: block; margin-top: 10px; padding: 10px; border-radius: 5px; background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb;';
        messageDiv.textContent = 'An error occurred. Please try again.';
      }
    });
  }
  
  // Delete account
  if (document.getElementById('deleteAccountBtn')) {
    document.getElementById('deleteAccountBtn').addEventListener('click', async () => {
      if (!confirm('Are you sure you want to delete your account? This action cannot be undone. All your data, animations, and avatars will be permanently deleted.')) {
        return;
      }
      
      if (!confirm('This is your final warning. Are you absolutely sure you want to delete your account?')) {
        return;
      }
      
      try {
        const response = await fetch('/api/account/delete', {
          method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
          showMessage('Account deleted successfully. Redirecting to home page...', 'success');
          setTimeout(() => {
            window.location.href = '/';
          }, 2000);
        } else {
          showMessage(data.message || 'Failed to delete account', 'error');
        }
      } catch (error) {
        showMessage('Delete failed: ' + error.message, 'error');
      }
    });
  }
  
  // Upload avatar
  if (document.getElementById('uploadAvatarBtn')) {
    document.getElementById('uploadAvatarBtn').addEventListener('click', async () => {
      const fileInput = document.getElementById('avatarUpload');
      const file = fileInput.files[0];
      
      if (!file) {
        showMessage('Please select an image', 'error');
        return;
      }
      
      const formData = new FormData();
      formData.append('avatar', file);
      
      try {
        const response = await fetch('/api/avatar/upload', {
          method: 'POST',
          body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
          showMessage(data.message, 'success');
          loadAvatars();
          fileInput.value = '';
        } else {
          showMessage(data.message, 'error');
        }
      } catch (error) {
        showMessage('Upload failed: ' + error.message, 'error');
      }
    });
  }
  
  // Load avatars
  async function loadAvatars() {
    try {
      const response = await fetch('/api/avatars');
      const data = await response.json();
      
      if (data.success) {
        const avatarList = document.getElementById('avatarList');
        const avatarSelect = document.getElementById('avatarSelect');
        
        avatarList.innerHTML = '';
        avatarSelect.innerHTML = '<option value="">--Select Avatar--</option>';
        
        data.avatars.forEach(avatar => {
          // Add to gallery
          const avatarDiv = document.createElement('div');
          avatarDiv.className = 'avatar-item';
          avatarDiv.innerHTML = `
            <img src="/static/${avatar.avatar_path}" alt="Avatar">
            <button class="btn small-btn danger-btn" onclick="deleteAvatar(${avatar.avatar_id})">Delete</button>
          `;
          avatarList.appendChild(avatarDiv);
          
          // Add to select
          const option = document.createElement('option');
          option.value = avatar.avatar_id;
          option.textContent = `Avatar ${avatar.avatar_id}`;
          avatarSelect.appendChild(option);
        });
      }
    } catch (error) {
      console.error('Error loading avatars:', error);
    }
  }
  
  // Delete avatar
  window.deleteAvatar = async (avatarId) => {
    if (!confirm('Delete this avatar?')) return;
    
    try {
      const response = await fetch(`/api/avatar/${avatarId}`, {
        method: 'DELETE'
      });
      
      const data = await response.json();
      
      if (data.success) {
        showMessage(data.message, 'success');
        loadAvatars();
      }
    } catch (error) {
      showMessage('Delete failed: ' + error.message, 'error');
    }
  };
  
  // Generate animation
  if (document.getElementById('generateBtn')) {
    document.getElementById('generateBtn').addEventListener('click', async () => {
      const avatarId = document.getElementById('avatarSelect').value;
      const expressionId = document.getElementById('expressionSelect').value;
      
      if (!avatarId || !expressionId) {
        showMessage('Please select avatar and expression', 'error');
        return;
      }
      
      try {
        const response = await fetch('/api/animation/generate', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ 
            avatar_id: avatarId, 
            expression_id: expressionId 
          })
        });
        
        const data = await response.json();
        
        if (data.success) {
          showMessage(data.message, 'success');
          
          // Show preview
          const preview = document.getElementById('animationPreview');
          const video = document.getElementById('previewVideo');
          video.src = `/static/${data.animation_path}`;
          preview.style.display = 'block';
          
          loadAnimations();
        } else {
          showMessage(data.message, 'error');
        }
      } catch (error) {
        showMessage('Generation failed: ' + error.message, 'error');
      }
    });
  }
  
  // Cancel preview
  if (document.getElementById('cancelPreviewBtn')) {
    document.getElementById('cancelPreviewBtn').addEventListener('click', () => {
      document.getElementById('animationPreview').style.display = 'none';
    });
  }
  
  // Load animations
  async function loadAnimations() {
    try {
      const response = await fetch('/api/animations');
      const data = await response.json();
      
      if (data.success) {
        const animationList = document.getElementById('animationList');
        animationList.innerHTML = '';
        
        data.animations.forEach(animation => {
          const animDiv = document.createElement('div');
          animDiv.className = 'animation-item';
          animDiv.innerHTML = `
            <video src="/static/${animation.animation_path}" controls></video>
            <p>${animation.expression_name || 'Custom'}</p>
            <p>${new Date(animation.created_at).toLocaleDateString()}</p>
          `;
          animationList.appendChild(animDiv);
        });
      }
    } catch (error) {
      console.error('Error loading animations:', error);
    }
  }
  
  // Initialize
  loadProfile();
  loadAvatars();
  loadAnimations();
}

// ============================================
// SUBSCRIBER DASHBOARD
// ============================================
if (window.location.pathname.includes('subscriber.html') || window.location.pathname === '/subscriber') {
  // Load profile
  async function loadProfile() {
    try {
      const response = await fetch('/api/profile');
      const data = await response.json();
      
      if (data.success) {
        document.getElementById('username').textContent = data.user.fullname;
        document.getElementById('email').textContent = data.user.email;
        
        // Update profile picture if available
        const profilePicture = document.getElementById('profilePicture');
        if (profilePicture) {
          if (data.user.profile_picture) {
            // User has a profile picture - load it
            const imageUrl = `/static/${data.user.profile_picture}?t=${Date.now()}`;
            console.log('📸 Setting profile picture src to:', imageUrl);
            profilePicture.src = imageUrl;
            
            // Force image reload
            profilePicture.onload = () => {
              console.log('✅ Profile picture loaded successfully');
            };
            profilePicture.onerror = () => {
              console.error('❌ Profile picture failed to load:', imageUrl);
              // Fallback to default image
              profilePicture.src = 'https://i.imgur.com/6VBx3io.png';
            };
          } else {
            // No profile picture - use default
            console.log('⚠️ No profile picture found in database for subscriber');
            profilePicture.src = 'https://i.imgur.com/6VBx3io.png';
          }
        } else {
          console.error('❌ Profile picture element not found!');
        }
      }
    } catch (error) {
      console.error('Error loading profile:', error);
    }
  }
  
  // Handle profile picture upload (same as user dashboard)
  const profilePictureInput = document.getElementById('profilePictureInput');
  if (profilePictureInput) {
    profilePictureInput.addEventListener('change', async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      
      const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp'];
      if (!allowedTypes.includes(file.type)) {
        alert('Invalid file type. Please upload a PNG, JPG, JPEG, GIF, or WEBP image.');
        return;
      }
      
      if (file.size > 5 * 1024 * 1024) {
        alert('File size too large. Please upload an image smaller than 5MB.');
        return;
      }
      
      const formData = new FormData();
      formData.append('profile_picture', file);
      
      const statusDiv = document.getElementById('profilePictureUploadStatus');
      if (statusDiv) {
        statusDiv.style.display = 'block';
        statusDiv.textContent = 'Uploading...';
        statusDiv.style.background = '#d1ecf1';
        statusDiv.style.color = '#0c5460';
      }
      
      try {
        const response = await fetch('/api/profile-picture', {
          method: 'POST',
          body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
          console.log('✅ Upload successful! Response:', data);
          const profilePicture = document.getElementById('profilePicture');
          if (profilePicture) {
            const imageUrl = `/static/${data.profile_picture}?t=${Date.now()}`;
            console.log('📸 Updating profile picture src to:', imageUrl);
            profilePicture.src = imageUrl;
            
            // Wait a moment then reload profile from database
            setTimeout(async () => {
              console.log('🔄 Reloading profile from database...');
              await loadProfile();
            }, 500);
          } else {
            console.error('❌ Profile picture element not found after upload!');
          }
          
          if (statusDiv) {
            statusDiv.textContent = 'Profile picture updated successfully!';
            statusDiv.style.background = '#d4edda';
            statusDiv.style.color = '#155724';
            setTimeout(() => {
              statusDiv.style.display = 'none';
            }, 3000);
          }
        } else {
          console.error('❌ Upload failed:', data.message);
          if (statusDiv) {
            statusDiv.textContent = `Error: ${data.message}`;
            statusDiv.style.background = '#f8d7da';
            statusDiv.style.color = '#721c24';
            setTimeout(() => {
              statusDiv.style.display = 'none';
            }, 5000);
          }
        }
      } catch (error) {
        console.error('Error uploading profile picture:', error);
        if (statusDiv) {
          statusDiv.textContent = 'Error uploading profile picture. Please try again.';
          statusDiv.style.background = '#f8d7da';
          statusDiv.style.color = '#721c24';
          setTimeout(() => {
            statusDiv.style.display = 'none';
          }, 5000);
        }
      }
      
      e.target.value = '';
    });
  }
  
  // Edit profile
  if (document.getElementById('editProfileBtn')) {
    document.getElementById('editProfileBtn').addEventListener('click', () => {
      document.getElementById('editProfileForm').style.display = 'block';
      document.getElementById('newUsername').value = document.getElementById('username').textContent;
      document.getElementById('newEmail').value = document.getElementById('email').textContent;
    });
  }
  
  if (document.getElementById('saveProfileBtn')) {
    document.getElementById('saveProfileBtn').addEventListener('click', async () => {
      const fullname = document.getElementById('newUsername').value;
      const email = document.getElementById('newEmail').value;
      
      try {
        const response = await fetch('/api/profile', {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ fullname, email })
        });
        
        const data = await response.json();
        
        if (data.success) {
          showMessage(data.message, 'success');
          document.getElementById('username').textContent = fullname;
          document.getElementById('email').textContent = email;
          document.getElementById('editProfileForm').style.display = 'none';
        }
      } catch (error) {
        showMessage('Update failed: ' + error.message, 'error');
      }
    });
  }
  
  if (document.getElementById('cancelEditBtn')) {
    document.getElementById('cancelEditBtn').addEventListener('click', () => {
      document.getElementById('editProfileForm').style.display = 'none';
    });
  }
  
  // Change password
  if (document.getElementById('changePasswordBtn')) {
    document.getElementById('changePasswordBtn').addEventListener('click', () => {
      const form = document.getElementById('changePasswordForm');
      form.style.display = form.style.display === 'none' ? 'block' : 'none';
      if (form.style.display === 'block') {
        document.getElementById('currentPassword').value = '';
        document.getElementById('newPassword').value = '';
        document.getElementById('confirmPassword').value = '';
        document.getElementById('passwordMessage').style.display = 'none';
      }
    });
  }
  
  if (document.getElementById('cancelPasswordBtn')) {
    document.getElementById('cancelPasswordBtn').addEventListener('click', () => {
      document.getElementById('changePasswordForm').style.display = 'none';
      document.getElementById('currentPassword').value = '';
      document.getElementById('newPassword').value = '';
      document.getElementById('confirmPassword').value = '';
      document.getElementById('passwordMessage').style.display = 'none';
    });
  }
  
  if (document.getElementById('savePasswordBtn')) {
    document.getElementById('savePasswordBtn').addEventListener('click', async () => {
      const currentPassword = document.getElementById('currentPassword').value;
      const newPassword = document.getElementById('newPassword').value;
      const confirmPassword = document.getElementById('confirmPassword').value;
      const messageDiv = document.getElementById('passwordMessage');
      
      if (!currentPassword || !newPassword || !confirmPassword) {
        messageDiv.style.display = 'block';
        messageDiv.style.cssText = 'display: block; margin-top: 10px; padding: 10px; border-radius: 5px; background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb;';
        messageDiv.textContent = 'All fields are required';
        return;
      }
      
      if (newPassword !== confirmPassword) {
        messageDiv.style.display = 'block';
        messageDiv.style.cssText = 'display: block; margin-top: 10px; padding: 10px; border-radius: 5px; background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb;';
        messageDiv.textContent = 'New passwords do not match';
        return;
      }
      
      if (newPassword.length < 6) {
        messageDiv.style.display = 'block';
        messageDiv.style.cssText = 'display: block; margin-top: 10px; padding: 10px; border-radius: 5px; background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb;';
        messageDiv.textContent = 'Password must be at least 6 characters long';
        return;
      }
      
      try {
        const response = await fetch('/api/change-password', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            current_password: currentPassword,
            new_password: newPassword,
            confirm_password: confirmPassword
          })
        });
        
        const data = await response.json();
        
        messageDiv.style.display = 'block';
        
        if (data.success) {
          messageDiv.style.cssText = 'display: block; margin-top: 10px; padding: 10px; border-radius: 5px; background: #d4edda; color: #155724; border: 1px solid #c3e6cb;';
          messageDiv.textContent = data.message;
          document.getElementById('currentPassword').value = '';
          document.getElementById('newPassword').value = '';
          document.getElementById('confirmPassword').value = '';
          setTimeout(() => {
            document.getElementById('changePasswordForm').style.display = 'none';
            messageDiv.style.display = 'none';
          }, 2000);
        } else {
          messageDiv.style.cssText = 'display: block; margin-top: 10px; padding: 10px; border-radius: 5px; background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb;';
          messageDiv.textContent = data.message || 'Failed to change password';
        }
      } catch (error) {
        messageDiv.style.display = 'block';
        messageDiv.style.cssText = 'display: block; margin-top: 10px; padding: 10px; border-radius: 5px; background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb;';
        messageDiv.textContent = 'An error occurred. Please try again.';
      }
    });
  }
  
  if (document.getElementById('updateSubscriptionBtn')) {
    document.getElementById('updateSubscriptionBtn').addEventListener('click', async () => {
      const plan = document.getElementById('planSelect').value;
      
      try {
        const response = await fetch('/api/subscription/update', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ plan })
        });
        
        const data = await response.json();
        
        if (data.success) {
          showMessage(data.message, 'success');
        }
      } catch (error) {
        showMessage('Update failed: ' + error.message, 'error');
      }
    });
  }
  
  // Delete account
  if (document.getElementById('deleteAccountBtn')) {
    document.getElementById('deleteAccountBtn').addEventListener('click', async () => {
      if (!confirm('Are you sure you want to delete your account? This action cannot be undone. All your data, animations, and avatars will be permanently deleted.')) {
        return;
      }
      
      if (!confirm('This is your final warning. Are you absolutely sure you want to delete your account?')) {
        return;
      }
      
      try {
        const response = await fetch('/api/account/delete', {
          method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
          showMessage('Account deleted successfully. Redirecting to home page...', 'success');
          setTimeout(() => {
            window.location.href = '/';
          }, 2000);
        } else {
          showMessage(data.message || 'Failed to delete account', 'error');
        }
      } catch (error) {
        showMessage('Delete failed: ' + error.message, 'error');
      }
    });
  }
  
  // Initialize subscriber dashboard
  loadProfile();
}

// ============================================
// ADMIN DASHBOARD
// ============================================
if (window.location.pathname.includes('admin.html') || window.location.pathname === '/admin') {
  let allUsers = [];
  
  // Load admin profile
  async function loadAdminProfile() {
    try {
      console.log('🔄 Loading profile for ADMIN...');
      const response = await fetch('/api/profile');
      const data = await response.json();
      
      console.log('📦 Profile data received:', data);
      
      if (data.success) {
        document.getElementById('adminUsername').textContent = data.user.fullname;
        document.getElementById('adminEmail').textContent = data.user.email;
        
        // Update profile picture if available
        const profilePicture = document.getElementById('profilePicture');
        if (profilePicture) {
          if (data.user.profile_picture) {
            // User has a profile picture - load it
            const imageUrl = `/static/${data.user.profile_picture}?t=${Date.now()}`;
            console.log('📸 Setting profile picture src to:', imageUrl);
            profilePicture.src = imageUrl;
            
            // Force image reload
            profilePicture.onload = () => {
              console.log('✅ Profile picture loaded successfully');
            };
            profilePicture.onerror = () => {
              console.error('❌ Profile picture failed to load:', imageUrl);
              // Fallback to default image
              profilePicture.src = 'https://i.imgur.com/6VBx3io.png';
            };
          } else {
            // No profile picture - use default
            console.log('⚠️ No profile picture found in database for admin');
            profilePicture.src = 'https://i.imgur.com/6VBx3io.png';
          }
        } else {
          console.error('❌ Profile picture element not found!');
        }
      }
    } catch (error) {
      console.error('❌ Error loading admin profile:', error);
    }
  }
  
  // Handle profile picture upload for admin
  const profilePictureInput = document.getElementById('profilePictureInput');
  if (profilePictureInput) {
    profilePictureInput.addEventListener('change', async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      
      const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp'];
      if (!allowedTypes.includes(file.type)) {
        alert('Invalid file type. Please upload a PNG, JPG, JPEG, GIF, or WEBP image.');
        return;
      }
      
      if (file.size > 5 * 1024 * 1024) {
        alert('File size too large. Please upload an image smaller than 5MB.');
        return;
      }
      
      const formData = new FormData();
      formData.append('profile_picture', file);
      
      const statusDiv = document.getElementById('profilePictureUploadStatus');
      if (statusDiv) {
        statusDiv.style.display = 'block';
        statusDiv.textContent = 'Uploading...';
        statusDiv.style.background = '#d1ecf1';
        statusDiv.style.color = '#0c5460';
      }
      
      try {
        const response = await fetch('/api/profile-picture', {
          method: 'POST',
          body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
          console.log('✅ Upload successful! Response:', data);
          const profilePicture = document.getElementById('profilePicture');
          if (profilePicture) {
            const imageUrl = `/static/${data.profile_picture}?t=${Date.now()}`;
            console.log('📸 Updating profile picture src to:', imageUrl);
            profilePicture.src = imageUrl;
            
            // Wait a moment then reload profile from database
            setTimeout(async () => {
              console.log('🔄 Reloading admin profile from database...');
              await loadAdminProfile();
            }, 500);
          } else {
            console.error('❌ Profile picture element not found after upload!');
          }
          
          if (statusDiv) {
            statusDiv.textContent = 'Profile picture updated successfully!';
            statusDiv.style.background = '#d4edda';
            statusDiv.style.color = '#155724';
            setTimeout(() => {
              statusDiv.style.display = 'none';
            }, 3000);
          }
        } else {
          console.error('❌ Upload failed:', data.message);
          if (statusDiv) {
            statusDiv.textContent = `Error: ${data.message}`;
            statusDiv.style.background = '#f8d7da';
            statusDiv.style.color = '#721c24';
            setTimeout(() => {
              statusDiv.style.display = 'none';
            }, 5000);
          }
        }
      } catch (error) {
        console.error('Error uploading profile picture:', error);
        if (statusDiv) {
          statusDiv.textContent = 'Error uploading profile picture. Please try again.';
          statusDiv.style.background = '#f8d7da';
          statusDiv.style.color = '#721c24';
          setTimeout(() => {
            statusDiv.style.display = 'none';
          }, 5000);
        }
      }
      
      e.target.value = '';
    });
  }
  
  // Edit admin profile
  if (document.getElementById('editAdminProfileBtn')) {
    document.getElementById('editAdminProfileBtn').addEventListener('click', () => {
      const form = document.getElementById('editAdminForm');
      form.style.display = form.style.display === 'none' ? 'block' : 'none';
      document.getElementById('newAdminUsername').value = document.getElementById('adminUsername').textContent;
      document.getElementById('newAdminEmail').value = document.getElementById('adminEmail').textContent;
    });
  }
  
  if (document.getElementById('saveAdminProfileBtn')) {
    document.getElementById('saveAdminProfileBtn').addEventListener('click', async () => {
      const fullname = document.getElementById('newAdminUsername').value;
      const email = document.getElementById('newAdminEmail').value;
      
      try {
        const response = await fetch('/api/profile', {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ fullname, email })
        });
        
        const data = await response.json();
        
        if (data.success) {
          showMessage(data.message, 'success');
          document.getElementById('adminUsername').textContent = fullname;
          document.getElementById('adminEmail').textContent = email;
          document.getElementById('editAdminForm').style.display = 'none';
        } else {
          showMessage(data.message, 'error');
        }
      } catch (error) {
        showMessage('Update failed: ' + error.message, 'error');
      }
    });
  }
  
  if (document.getElementById('cancelAdminEditBtn')) {
    document.getElementById('cancelAdminEditBtn').addEventListener('click', () => {
      document.getElementById('editAdminForm').style.display = 'none';
    });
  }
  
  // Change password
  if (document.getElementById('changePasswordBtn')) {
    document.getElementById('changePasswordBtn').addEventListener('click', () => {
      const form = document.getElementById('changePasswordForm');
      form.style.display = form.style.display === 'none' ? 'block' : 'none';
      if (form.style.display === 'block') {
        document.getElementById('currentPassword').value = '';
        document.getElementById('newPassword').value = '';
        document.getElementById('confirmPassword').value = '';
        document.getElementById('passwordMessage').style.display = 'none';
      }
    });
  }
  
  if (document.getElementById('cancelPasswordBtn')) {
    document.getElementById('cancelPasswordBtn').addEventListener('click', () => {
      document.getElementById('changePasswordForm').style.display = 'none';
      document.getElementById('currentPassword').value = '';
      document.getElementById('newPassword').value = '';
      document.getElementById('confirmPassword').value = '';
      document.getElementById('passwordMessage').style.display = 'none';
    });
  }
  
  if (document.getElementById('savePasswordBtn')) {
    document.getElementById('savePasswordBtn').addEventListener('click', async () => {
      const currentPassword = document.getElementById('currentPassword').value;
      const newPassword = document.getElementById('newPassword').value;
      const confirmPassword = document.getElementById('confirmPassword').value;
      const messageDiv = document.getElementById('passwordMessage');
      
      if (!currentPassword || !newPassword || !confirmPassword) {
        messageDiv.style.display = 'block';
        messageDiv.style.cssText = 'display: block; margin-top: 10px; padding: 10px; border-radius: 5px; background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb;';
        messageDiv.textContent = 'All fields are required';
        return;
      }
      
      if (newPassword !== confirmPassword) {
        messageDiv.style.display = 'block';
        messageDiv.style.cssText = 'display: block; margin-top: 10px; padding: 10px; border-radius: 5px; background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb;';
        messageDiv.textContent = 'New passwords do not match';
        return;
      }
      
      if (newPassword.length < 6) {
        messageDiv.style.display = 'block';
        messageDiv.style.cssText = 'display: block; margin-top: 10px; padding: 10px; border-radius: 5px; background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb;';
        messageDiv.textContent = 'Password must be at least 6 characters long';
        return;
      }
      
      try {
        const response = await fetch('/api/change-password', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            current_password: currentPassword,
            new_password: newPassword,
            confirm_password: confirmPassword
          })
        });
        
        const data = await response.json();
        
        messageDiv.style.display = 'block';
        
        if (data.success) {
          messageDiv.style.cssText = 'display: block; margin-top: 10px; padding: 10px; border-radius: 5px; background: #d4edda; color: #155724; border: 1px solid #c3e6cb;';
          messageDiv.textContent = data.message;
          document.getElementById('currentPassword').value = '';
          document.getElementById('newPassword').value = '';
          document.getElementById('confirmPassword').value = '';
          setTimeout(() => {
            document.getElementById('changePasswordForm').style.display = 'none';
            messageDiv.style.display = 'none';
          }, 2000);
        } else {
          messageDiv.style.cssText = 'display: block; margin-top: 10px; padding: 10px; border-radius: 5px; background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb;';
          messageDiv.textContent = data.message || 'Failed to change password';
        }
      } catch (error) {
        messageDiv.style.display = 'block';
        messageDiv.style.cssText = 'display: block; margin-top: 10px; padding: 10px; border-radius: 5px; background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb;';
        messageDiv.textContent = 'An error occurred. Please try again.';
      }
    });
  }
  
  // Load all users
  async function loadUsers() {
    try {
      const response = await fetch('/api/admin/users');
      const data = await response.json();
      
      if (data.success) {
        allUsers = data.users;
        displayUsers(allUsers);
      } else {
        showMessage(data.message || 'Failed to load users', 'error');
      }
    } catch (error) {
      console.error('Error loading users:', error);
      showMessage('Error loading users: ' + error.message, 'error');
    }
  }
  
  // Display users
  function displayUsers(users) {
    const userList = document.getElementById('userList');
    userList.innerHTML = '';
    
    if (users.length === 0) {
      userList.innerHTML = '<p style="padding: 20px; text-align: center; color: #666;">No users found</p>';
      return;
    }
    
    const table = document.createElement('table');
    table.style.cssText = 'width: 100%; border-collapse: collapse; margin-top: 10px;';
    table.innerHTML = `
      <thead>
        <tr style="background: #009688; color: white;">
          <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">ID</th>
          <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Full Name</th>
          <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Email</th>
          <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Role</th>
          <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Status</th>
          <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Created</th>
          <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Actions</th>
        </tr>
      </thead>
      <tbody id="userTableBody"></tbody>
    `;
    
    const tbody = table.querySelector('#userTableBody');
    
    users.forEach(user => {
      const row = document.createElement('tr');
      row.style.cssText = 'border-bottom: 1px solid #ddd;';
      row.innerHTML = `
        <td style="padding: 10px; border: 1px solid #ddd;">${user.user_id}</td>
        <td style="padding: 10px; border: 1px solid #ddd;">${user.fullname}</td>
        <td style="padding: 10px; border: 1px solid #ddd;">${user.email}</td>
        <td style="padding: 10px; border: 1px solid #ddd;">
          <span style="padding: 4px 8px; border-radius: 4px; background: ${getRoleColor(user.role)}; color: white; font-size: 12px;">
            ${user.role}
          </span>
        </td>
        <td style="padding: 10px; border: 1px solid #ddd;">
          <span style="padding: 4px 8px; border-radius: 4px; background: ${getStatusColor(user.subscription_status)}; color: white; font-size: 12px;">
            ${user.subscription_status}
          </span>
        </td>
        <td style="padding: 10px; border: 1px solid #ddd;">${new Date(user.created_at).toLocaleDateString()}</td>
        <td style="padding: 10px; border: 1px solid #ddd;">
          <button class="btn small-btn" onclick="window.editUser(${user.user_id}, ${JSON.stringify(user.fullname)}, ${JSON.stringify(user.email)})" style="margin: 2px;">Edit</button>
          ${user.subscription_status === 'suspended' 
            ? `<button class="btn small-btn" onclick="activateUser(${user.user_id})" style="margin: 2px;">Activate</button>`
            : `<button class="btn small-btn danger-btn" onclick="suspendUser(${user.user_id})" style="margin: 2px;">Suspend</button>`
          }
          <button class="btn small-btn danger-btn" onclick="deleteUser(${user.user_id})" style="margin: 2px;">Delete</button>
        </td>
      `;
      tbody.appendChild(row);
    });
    
    userList.appendChild(table);
  }
  
  function getRoleColor(role) {
    const colors = {
      'admin': '#d32f2f',
      'subscriber': '#1976d2',
      'user': '#388e3c'
    };
    return colors[role] || '#757575';
  }
  
  function getStatusColor(status) {
    const colors = {
      'active': '#388e3c',
      'inactive': '#757575',
      'suspended': '#d32f2f'
    };
    return colors[status] || '#757575';
  }
  
  // Search users
  if (document.getElementById('searchUserBtn')) {
    document.getElementById('searchUserBtn').addEventListener('click', () => {
      const searchTerm = document.getElementById('searchUser').value.toLowerCase().trim();
      
      if (!searchTerm) {
        displayUsers(allUsers);
        return;
      }
      
      const filtered = allUsers.filter(user => 
        user.email.toLowerCase().includes(searchTerm) ||
        user.fullname.toLowerCase().includes(searchTerm)
      );
      
      displayUsers(filtered);
    });
  }
  
  // Search on Enter key
  if (document.getElementById('searchUser')) {
    document.getElementById('searchUser').addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        document.getElementById('searchUserBtn').click();
      }
    });
  }
  
  // Load all users button
  if (document.getElementById('loadAllUsersBtn')) {
    document.getElementById('loadAllUsersBtn').addEventListener('click', () => {
      document.getElementById('searchUser').value = '';
      loadUsers();
    });
  }
  
  // Suspend user
  window.suspendUser = async (userId) => {
    if (!confirm('Are you sure you want to suspend this user?')) return;
    
    try {
      const response = await fetch(`/api/admin/user/${userId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ action: 'suspend' })
      });
      
      const data = await response.json();
      if (data.success) {
        showMessage(data.message, 'success');
        loadUsers();
      } else {
        showMessage(data.message || 'Failed to suspend user', 'error');
      }
    } catch (error) {
      showMessage('Action failed: ' + error.message, 'error');
    }
  };
  
  // Activate user
  window.activateUser = async (userId) => {
    if (!confirm('Are you sure you want to activate this user?')) return;
    
    try {
      const response = await fetch(`/api/admin/user/${userId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ action: 'activate' })
      });
      
      const data = await response.json();
      if (data.success) {
        showMessage(data.message, 'success');
        loadUsers();
      } else {
        showMessage(data.message || 'Failed to activate user', 'error');
      }
    } catch (error) {
      showMessage('Action failed: ' + error.message, 'error');
    }
  };
  
  // Edit user (fullname and email only) - Make sure it's globally available
  window.editUser = function(userId, currentFullname, currentEmail) {
    console.log('Edit user called:', userId, currentFullname, currentEmail);
    const newFullname = prompt('Enter new full name:', currentFullname);
    if (newFullname === null) return;
    
    const newEmail = prompt('Enter new email:', currentEmail);
    if (newEmail === null) return;
    
    if (!newFullname.trim() || !newEmail.trim()) {
      showMessage('Full name and email are required', 'error');
      return;
    }
    
    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(newEmail.trim())) {
      showMessage('Please enter a valid email address', 'error');
      return;
    }
    
    updateUser(userId, newFullname.trim(), newEmail.trim());
  };
  
  async function updateUser(userId, fullname, email) {
    try {
      const response = await fetch(`/api/admin/user/${userId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
          action: 'edit',
          fullname: fullname,
          email: email
        })
      });
      
      const data = await response.json();
      if (data.success) {
        showMessage(data.message, 'success');
        loadUsers();
      } else {
        showMessage(data.message || 'Failed to update user', 'error');
      }
    } catch (error) {
      showMessage('Update failed: ' + error.message, 'error');
    }
  }
  
  // Delete user
  window.deleteUser = async (userId) => {
    if (!confirm('Are you sure you want to DELETE this user? This action cannot be undone!')) return;
    
    try {
      const response = await fetch(`/api/admin/user/${userId}`, {
        method: 'DELETE'
      });
      
      const data = await response.json();
      if (data.success) {
        showMessage(data.message, 'success');
        loadUsers();
      } else {
        showMessage(data.message || 'Failed to delete user', 'error');
      }
    } catch (error) {
      showMessage('Delete failed: ' + error.message, 'error');
    }
  };
  
  if (document.getElementById('updateSubscriptionBtn')) {
    document.getElementById('updateSubscriptionBtn').addEventListener('click', async () => {
      const plan = document.getElementById('planSelect').value;
      
      try {
        const response = await fetch('/api/subscription/update', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ plan })
        });
        
        const data = await response.json();
        
        if (data.success) {
          showMessage(data.message, 'success');
        }
      } catch (error) {
        showMessage('Update failed: ' + error.message, 'error');
      }
    });
  }
  
  // Initialize admin dashboard
  loadAdminProfile();
  loadUsers();
}

// ============================================
// LOGOUT FUNCTIONALITY
// ============================================
const logoutButtons = document.querySelectorAll('#logoutBtn, #logoutAdminBtn');
logoutButtons.forEach(btn => {
  if (btn) {
    btn.addEventListener('click', async () => {
      try {
        const response = await fetch('/api/logout', {
          method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
          window.location.href = '/login';
        }
      } catch (error) {
        console.error('Logout failed:', error);
      }
    });
  }
});