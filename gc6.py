import streamlit as st
import json
import os
from datetime import datetime
from uuid import uuid4
import time
import base64
from PIL import Image
import io

# Page configuration
st.set_page_config(
    page_title="Chat With Shuvo",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded"
)


def format_message_time():
    return datetime.now().strftime("%H:%M:%S")


def save_media_file(uploaded_file, message_id):
    """Save uploaded media file and return the file path"""
    try:
        if not os.path.exists("database/media"):
            os.makedirs("database/media")

        # Generate unique filename
        file_extension = uploaded_file.name.split('.')[-1]
        filename = f"{message_id}.{file_extension}"
        file_path = f"database/media/{filename}"

        # Save file
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        return file_path
    except Exception as e:
        st.error(f"Error saving media file: {e}")
        return None


def get_file_size_mb(file_path):
    """Get file size in MB"""
    try:
        size_bytes = os.path.getsize(file_path)
        return size_bytes / (1024 * 1024)
    except:
        return 0


def is_image_file(filename):
    """Check if file is an image"""
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
    return any(filename.lower().endswith(ext) for ext in image_extensions)


def is_video_file(filename):
    """Check if file is a video"""
    video_extensions = ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv']
    return any(filename.lower().endswith(ext) for ext in video_extensions)


def save_private_chat_message(user_id, message):
    """Save message to specific user's private chat with admin"""
    try:
        if not os.path.exists("database/private_chats"):
            os.makedirs("database/private_chats")

        chat_file = f"database/private_chats/{user_id}.json"

        if os.path.exists(chat_file):
            with open(chat_file, "r") as f:
                chat_data = json.load(f)
        else:
            chat_data = {
                "user_id": user_id,
                "messages": [],
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat()
            }

        chat_data["messages"].append(message)
        chat_data["last_updated"] = datetime.now().isoformat()

        # Keep only last 500 messages per chat
        if len(chat_data["messages"]) > 500:
            chat_data["messages"] = chat_data["messages"][-500:]

        with open(chat_file, "w") as f:
            json.dump(chat_data, f, indent=2)
    except Exception:
        pass


def load_private_chat(user_id):
    """Load private chat messages for specific user"""
    try:
        chat_file = f"database/private_chats/{user_id}.json"

        if os.path.exists(chat_file):
            with open(chat_file, "r") as f:
                chat_data = json.load(f)
            return chat_data.get("messages", [])
        return []
    except Exception:
        return []


def get_all_user_chats():
    """Get list of all users who have chatted with admin"""
    try:
        if not os.path.exists("database/private_chats"):
            return []

        user_chats = []
        for filename in os.listdir("database/private_chats"):
            if filename.endswith(".json"):
                user_id = filename[:-5]  # Remove .json extension
                try:
                    with open(f"database/private_chats/{filename}", "r") as f:
                        chat_data = json.load(f)

                    # Get last message info
                    messages = chat_data.get("messages", [])
                    last_message = messages[-1] if messages else None
                    unread_count = sum(
                        1 for msg in messages if msg.get("sender") != "admin" and not msg.get("read_by_admin", False))

                    user_chats.append({
                        "user_id": user_id,
                        "last_updated": chat_data.get("last_updated", ""),
                        "message_count": len(messages),
                        "last_message": last_message,
                        "unread_count": unread_count
                    })
                except:
                    continue

        # Sort by last updated (most recent first)
        user_chats.sort(key=lambda x: x["last_updated"], reverse=True)
        return user_chats
    except Exception:
        return []


def mark_messages_as_read(user_id):
    """Mark all user messages as read by admin"""
    try:
        chat_file = f"database/private_chats/{user_id}.json"
        if os.path.exists(chat_file):
            with open(chat_file, "r") as f:
                chat_data = json.load(f)

            # Mark all user messages as read
            for message in chat_data["messages"]:
                if message.get("sender") != "admin":
                    message["read_by_admin"] = True

            with open(chat_file, "w") as f:
                json.dump(chat_data, f, indent=2)
    except Exception:
        pass


def clear_user_chat(user_id):
    """Clear specific user's chat"""
    try:
        chat_file = f"database/private_chats/{user_id}.json"
        if os.path.exists(chat_file):
            os.remove(chat_file)
    except Exception:
        pass


def initialize_session():
    if "current_user" not in st.session_state:
        st.session_state.current_user = ""
    if "is_authenticated" not in st.session_state:
        st.session_state.is_authenticated = False
    if "is_admin" not in st.session_state:
        st.session_state.is_admin = False
    if "show_media_uploader" not in st.session_state:
        st.session_state.show_media_uploader = False
    if "admin_login_mode" not in st.session_state:
        st.session_state.admin_login_mode = False
    if "temp_username" not in st.session_state:
        st.session_state.temp_username = ""
    if "selected_user_chat" not in st.session_state:
        st.session_state.selected_user_chat = None
    if "admin_view_mode" not in st.session_state:
        st.session_state.admin_view_mode = "inbox"
    if "auto_refresh_time" not in st.session_state:
        st.session_state.auto_refresh_time = 3
    if "last_refresh" not in st.session_state:
        st.session_state.last_refresh = time.time()
    if "auto_refresh_enabled" not in st.session_state:
        st.session_state.auto_refresh_enabled = True


def authenticate_user(username, password=None):
    """Authenticate user - admin needs password, regular users don't"""
    # Admin credentials
    ADMIN_USERNAME = "Ariyan"
    ADMIN_PASSWORD = "Ariyan007"

    if username == ADMIN_USERNAME:
        # Admin login requires password
        if password == ADMIN_PASSWORD:
            return True, True  # authenticated, is_admin
        else:
            return False, False  # authentication failed
    else:
        # Regular users only need username
        if username and username.strip():
            return True, False  # authenticated, not admin
        else:
            return False, False  # no username provided


def display_media_message(message, is_sender):
    """Display a message with media content"""
    content = message.get("content", "")
    timestamp = message.get("timestamp", "")
    sender = message.get("sender", "")
    media_path = message.get("media_path", "")
    media_type = message.get("media_type", "")
    original_filename = message.get("original_filename", "")

    alignment = "message-row-right" if is_sender else "message-row-left"
    sender_name = "You" if is_sender else ("Admin" if sender == "admin" else sender)
    sender_prefix = f"<strong>{sender_name}:</strong> " if not is_sender else ""

    media_html = ""

    if media_path and os.path.exists(media_path):
        if media_type == "image":
            try:
                # Display image
                image = Image.open(media_path)
                # Resize if too large
                max_width = 400
                if image.width > max_width:
                    ratio = max_width / image.width
                    new_height = int(image.height * ratio)
                    image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)

                # Convert to base64 for display
                buffered = io.BytesIO()
                image.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()

                media_html = f'''
                <div style="margin: 8px 0;">
                    <img src="data:image/png;base64,{img_str}" 
                         style="max-width: 100%; border-radius: 8px; cursor: pointer;"
                         onclick="window.open('data:image/png;base64,{img_str}', '_blank')"
                         title="Click to view full size">
                    <div style="font-size: 0.75em; color: #888; margin-top: 4px;">📷 {original_filename}</div>
                </div>
                '''
            except Exception as e:
                media_html = f'<div style="color: #ff6b6b;">Error loading image: {original_filename}</div>'

        elif media_type == "video":
            try:
                file_size = get_file_size_mb(media_path)
                media_html = f'''
                <div style="margin: 8px 0; padding: 12px; background: rgba(0,0,0,0.1); border-radius: 8px;">
                    <div style="font-size: 1.1em;">🎥 {original_filename}</div>
                    <div style="font-size: 0.85em; color: #666; margin-top: 4px;">
                        Video • {file_size:.1f} MB
                    </div>
                    <div style="margin-top: 8px;">
                        <em style="font-size: 0.8em; color: #888;">
                            💡 Video files can be downloaded from the server directory: {media_path}
                        </em>
                    </div>
                </div>
                '''
            except Exception as e:
                media_html = f'<div style="color: #ff6b6b;">Error loading video: {original_filename}</div>'

    # Combine text and media
    message_content = ""
    if content.strip():
        message_content += f"<div>{sender_prefix}{content}</div>"
    if media_html:
        message_content += media_html

    st.markdown(f"""
    <div class="{alignment}">
        <div class="message-content">
            {message_content}
            <div class="message-time">🕐 {timestamp}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def show_login_page():
    """Display login/authentication page"""
    st.title("Hey")
    st.markdown("Welcome! Enter your username to start chatting")
    st.markdown("---")

    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("Enter Username")

        with st.form("username_form", clear_on_submit=False):
            username = st.text_input(
                "Your Username:",
                placeholder="Enter your username...",
                help="Choose any username to start chatting"
            )

            # Two columns for buttons
            btn_col1, btn_col2 = st.columns(2)

            with btn_col1:
                user_submit = st.form_submit_button("💬 Start Chat", use_container_width=True, type="primary")

            with btn_col2:
                admin_mode = st.form_submit_button("Admin Login", use_container_width=True)

            # Handle regular user login
            if user_submit:
                if username and username.strip():
                    # Check if it's admin username without password
                    if username.strip() == "Ariyan":
                        st.error("Admin username detected!")
                    else:
                        is_authenticated, is_admin = authenticate_user(username.strip())
                        if is_authenticated:
                            st.session_state.current_user = username.strip()
                            st.session_state.is_authenticated = True
                            st.session_state.is_admin = is_admin
                            st.success(f"Welcome!, {username}!")
                            time.sleep(1.5)
                            st.rerun()
                        else:
                            st.error("Authentication failed!")
                else:
                    st.error("Please enter a username!")

            # Handle admin login
            if admin_mode:
                if username and username.strip():
                    # Only allow admin login if username is exactly "Ariyan"
                    if username.strip() == "Ariyan":
                        st.session_state.admin_login_mode = True
                        st.session_state.temp_username = username.strip()
                        st.rerun()
                    else:
                        st.error("❌ Admin login not available")
                else:
                    st.error("❌ Please enter the admin username first!")

    # Show admin password form if admin mode is activated
    if st.session_state.get("admin_login_mode", False):
        st.markdown("---")
        with col2:
            st.markdown("Admin Password Required")
            st.info(f"Username: **{st.session_state.temp_username}**")

            with st.form("admin_password_form"):
                admin_password = st.text_input("Admin Password:", type="password", placeholder="Enter admin password")

                pwd_col1, pwd_col2 = st.columns(2)
                with pwd_col1:
                    admin_submit = st.form_submit_button("Login as Admin", use_container_width=True, type="primary")
                with pwd_col2:
                    cancel_admin = st.form_submit_button("Cancel", use_container_width=True)

                if admin_submit:
                    if admin_password:
                        is_authenticated, is_admin = authenticate_user(st.session_state.temp_username, admin_password)
                        if is_authenticated:
                            st.session_state.current_user = st.session_state.temp_username
                            st.session_state.is_authenticated = True
                            st.session_state.is_admin = is_admin
                            st.session_state.admin_login_mode = False
                            st.session_state.temp_username = ""

                            if is_admin:
                                st.success(f"Welcome to Admin Dashboard, {st.session_state.current_user}!")
                            else:
                                st.success(f"Welcome, {st.session_state.current_user}!")
                            time.sleep(1.5)
                            st.rerun()
                        else:
                            st.error("Invalid admin credentials!")
                    else:
                        st.error("Please enter the admin password!")

                if cancel_admin:
                    st.session_state.admin_login_mode = False
                    st.session_state.temp_username = ""
                    st.rerun()

    # Additional info at bottom
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.9em;">
        <p>💬 <strong>Private Admin Chat:</strong> Direct communication with the Admin</p>
        <p>📎 <strong>Features:</strong> Send text messages, images, and videos</p>
        <p>🔒 <strong>Admin:</strong> Manage all user conversations from a central inbox</p>
    </div>
    """, unsafe_allow_html=True)


def show_admin_inbox():
    """Show admin inbox with all user chats"""
    st.title("Admin Inbox")
    st.markdown("Manage all user conversations from here")

    # Get all user chats
    user_chats = get_all_user_chats()

    if not user_chats:
        st.info("No user conversations yet. Users will appear here when they start chatting.")
        return

    # Stats
    total_users = len(user_chats)
    total_unread = sum(chat["unread_count"] for chat in user_chats)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Users", total_users)
    with col2:
        st.metric("Unread Messages", total_unread)
    with col3:
        if st.button("Refresh Inbox"):
            st.rerun()

    st.markdown("---")

    # User list
    for chat in user_chats:
        user_id = chat["user_id"]
        unread_count = chat["unread_count"]
        last_message = chat["last_message"]

        # Create container for each user
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 2, 1, 1])

            with col1:
                # User info
                unread_badge = f" 🔴({unread_count})" if unread_count > 0 else ""
                st.markdown(f"**👤 {user_id}**{unread_badge}")

                # Last message preview
                if last_message:
                    preview = last_message.get("content", "")
                    if last_message.get("media_path"):
                        media_type = last_message.get("media_type", "file")
                        preview = f"📎 {media_type.title()}: {preview}" if preview else f"📎 {media_type.title()} file"

                    if len(preview) > 50:
                        preview = preview[:50] + "..."

                    sender = last_message.get("sender", "")
                    sender_label = "You: " if sender == "admin" else f"{sender}: "
                    st.caption(f"{sender_label}{preview}")
                else:
                    st.caption("No messages yet")

            with col2:
                # Last updated
                if chat["last_updated"]:
                    try:
                        last_time = datetime.fromisoformat(chat["last_updated"]).strftime("%m/%d %H:%M")
                        st.caption(f"🕐 {last_time}")
                    except:
                        st.caption("🕐 Recently")

                st.caption(f"💬 {chat['message_count']} messages")

            with col3:
                if st.button("💬 Open", key=f"open_{user_id}"):
                    st.session_state.selected_user_chat = user_id
                    st.session_state.admin_view_mode = "chat"
                    # Mark messages as read when admin opens chat
                    mark_messages_as_read(user_id)
                    st.rerun()

            with col4:
                if st.button("🗑️", key=f"delete_{user_id}", help="Delete conversation"):
                    clear_user_chat(user_id)
                    st.success(f"Deleted conversation with {user_id}")
                    st.rerun()

        st.divider()


def show_admin_chat_view():
    """Show admin chat interface with specific user"""
    user_id = st.session_state.selected_user_chat

    # Header
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.title(f"💬 Chat with {user_id}")
    with col2:
        if st.button("📧 Back to Inbox"):
            st.session_state.admin_view_mode = "inbox"
            st.session_state.selected_user_chat = None
            st.rerun()
    with col3:
        if st.button("🗑️ Clear Chat"):
            clear_user_chat(user_id)
            st.success(f"Cleared chat with {user_id}")
            st.session_state.admin_view_mode = "inbox"
            st.session_state.selected_user_chat = None
            st.rerun()

    # Load messages
    messages = load_private_chat(user_id)

    # Display messages
    show_chat_messages(messages, "admin")

    # Admin input section
    show_admin_input_section(user_id)


def show_user_chat_view():
    """Show user chat interface with admin"""
    user_id = st.session_state.current_user

    st.title("💬 Chat with Shuvo")
    st.markdown(f"**Your Username:** {user_id}")
    st.markdown("---")

    # Load messages
    messages = load_private_chat(user_id)

    # Display messages
    show_chat_messages(messages, user_id)

    # User input section
    show_user_input_section()


def show_chat_messages(messages, current_user_id):
    if messages:
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)

        for message in messages[-50:]:
            sender = message.get("sender", "")
            is_sender = (sender == current_user_id) or (current_user_id == "admin" and sender == "admin")

            if message.get("media_path"):
                display_media_message(message, is_sender)
            else:
                content = message.get("content", "")
                timestamp = message.get("timestamp", "")

                if is_sender:
                    st.markdown(f"""
                    <div class="message-row-right">
                        <div class="message-content">
                            <div>{content}</div>
                            <div class="message-time">🕐 {timestamp}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    sender_name = "Admin" if sender == "admin" else sender
                    st.markdown(f"""
                    <div class="message-row-left">
                        <div class="message-content">
                            <div><strong>{sender_name}:</strong> {content}</div>
                            <div class="message-time">🕐 {timestamp}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="text-align: center; padding: 40px 20px; background: rgba(0,0,0,0.05); border-radius: 10px; margin: 20px 0; border: 1px solid #333;">
            <div style="font-size: 2.5em; margin-bottom: 15px;">💬</div>
            <h3 style="color: #666; margin-bottom: 8px; font-size: 1.2em;">No messages yet</h3>
            <p style="color: #888; font-size: 0.9em;">Start the conversation!</p>
        </div>
        """, unsafe_allow_html=True)

    current_time = time.time()
    time_since_last_refresh = current_time - st.session_state.last_refresh

    if st.session_state.auto_refresh_enabled and time_since_last_refresh >= st.session_state.auto_refresh_time:
        st.session_state.last_refresh = current_time
        st.rerun()


def show_user_input_section():
    """Show input section for regular users"""
    user_id = st.session_state.current_user

    # Media upload section
    if st.session_state.show_media_uploader:
        st.markdown('<div class="media-upload-section">', unsafe_allow_html=True)
        st.subheader("📎 Send Media")

        col1, col2 = st.columns([2, 1])
        with col1:
            uploaded_file = st.file_uploader(
                "Choose an image or video file",
                type=['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv'],
                help="Supported formats: Images (JPG, PNG, GIF, etc.) and Videos (MP4, AVI, MOV, etc.)"
            )
        with col2:
            media_caption = st.text_area("Caption (optional)", height=100, placeholder="Add a caption...")

        if uploaded_file is not None:
            file_size_mb = len(uploaded_file.getbuffer()) / (1024 * 1024)
            st.info(f"📄 **{uploaded_file.name}** • {file_size_mb:.1f} MB")

            if file_size_mb > 50:
                st.error("❌ File too large! choose a file smaller than 50MB.")
            else:
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("📤 Send", type="primary"):
                        message_id = str(uuid4())
                        media_path = save_media_file(uploaded_file, message_id)

                        if media_path:
                            media_type = "image" if is_image_file(uploaded_file.name) else "video"

                            user_message = {
                                "message_id": message_id,
                                "content": media_caption.strip(),
                                "timestamp": format_message_time(),
                                "sender": user_id,
                                "media_path": media_path,
                                "media_type": media_type,
                                "original_filename": uploaded_file.name
                            }

                            save_private_chat_message(user_id, user_message)
                            st.session_state.show_media_uploader = False
                            st.success("✅ Media sent!")
                            st.rerun()
                        else:
                            st.error("Failed to save media file!")

                with col2:
                    if st.button("Cancel"):
                        st.session_state.show_media_uploader = False
                        st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    # Text input section
    col1, col2 = st.columns([4, 1])
    with col1:
        if user_message := st.chat_input("Type your message..."):
            message = {
                "message_id": str(uuid4()),
                "content": user_message,
                "timestamp": format_message_time(),
                "sender": user_id
            }

            save_private_chat_message(user_id, message)
            st.rerun()

    with col2:
        if st.button("📎 Media", use_container_width=True, help="Send images or videos"):
            st.session_state.show_media_uploader = not st.session_state.show_media_uploader
            st.rerun()


def show_admin_input_section(target_user_id):
    """Show input section for admin to reply to specific user"""
    # Media upload section for admin
    if st.session_state.show_media_uploader:
        st.markdown('<div class="media-upload-section">', unsafe_allow_html=True)
        st.subheader(f"📎 Send Media to {target_user_id}")

        col1, col2 = st.columns([2, 1])
        with col1:
            uploaded_file = st.file_uploader(
                "Choose an image or video file",
                type=['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv'],
                help="Supported formats: Images (JPG, PNG, GIF, etc.) and Videos (MP4, AVI, MOV, etc.)",
                key="admin_media_upload"
            )
        with col2:
            media_caption = st.text_area("Caption (optional)", height=100, placeholder="Add a caption...",
                                         key="admin_caption")

        if uploaded_file is not None:
            file_size_mb = len(uploaded_file.getbuffer()) / (1024 * 1024)
            st.info(f"📄 **{uploaded_file.name}** • {file_size_mb:.1f} MB")

            if file_size_mb > 50:
                st.error("File too large! Please choose a file smaller than 50MB.")
            else:
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("📤 Send to User", type="primary", key="admin_send_media"):
                        message_id = str(uuid4())
                        media_path = save_media_file(uploaded_file, message_id)

                        if media_path:
                            media_type = "image" if is_image_file(uploaded_file.name) else "video"

                            admin_message = {
                                "message_id": message_id,
                                "content": media_caption.strip(),
                                "timestamp": format_message_time(),
                                "sender": "admin",
                                "media_path": media_path,
                                "media_type": media_type,
                                "original_filename": uploaded_file.name
                            }

                            save_private_chat_message(target_user_id, admin_message)
                            st.session_state.show_media_uploader = False
                            st.success(f"Media sent to {target_user_id}!")
                            st.rerun()
                        else:
                            st.error("Failed to save media file!")

                with col2:
                    if st.button("Cancel", key="admin_cancel_media"):
                        st.session_state.show_media_uploader = False
                        st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    # Text input section for admin
    col1, col2 = st.columns([4, 1])
    with col1:
        admin_message_key = f"admin_message_{target_user_id}"
        if admin_message := st.chat_input(f"Reply to {target_user_id}...", key=admin_message_key):
            message = {
                "message_id": str(uuid4()),
                "content": admin_message,
                "timestamp": format_message_time(),
                "sender": "admin"
            }

            save_private_chat_message(target_user_id, message)
            st.rerun()

    with col2:
        if st.button("📎 Media", use_container_width=True, help="Send images or videos", key="admin_media_toggle"):
            st.session_state.show_media_uploader = not st.session_state.show_media_uploader
            st.rerun()


def main():
    initialize_session()

    st.markdown("""
    <style>
    .chat-container {
        display: flex;
        flex-direction: column;
        gap: 1rem;
        max-height: 400px;
        overflow-y: auto;
        padding: 15px;
        border: 1px solid #333;
        border-radius: 10px;
        margin-bottom: 20px;
        background: var(--chat-bg-color);
    }
    .message-row-right {
        display: flex;
        justify-content: flex-end;
        width: 100%;
    }
    .message-row-left {
        display: flex;
        justify-content: flex-start;
        width: 100%;
    }
    .message-content {
        max-width: 70%;
        padding: 0.75rem;
        border-radius: 0.5rem;
        margin: 0.25rem;
        background-color: var(--background-color);
        border: 1px solid var(--border-color);
        color: var(--text-color);
    }
    .message-time {
        font-size: 0.8rem;
        color: var(--secondary-text-color);
        margin-top: 0.25rem;
    }
    .media-upload-section {
        background: rgba(0,0,0,0.05);
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        border: 2px dashed #ccc;
    }

    [data-theme="dark"] .message-content,
    .stApp[data-theme="dark"] .message-content,
    .message-content {
        background-color: #2b2b2b !important;
        border: 1px solid #404040 !important;
        color: #ffffff !important;
    }

    [data-theme="dark"] .chat-container,
    .stApp[data-theme="dark"] .chat-container,
    .chat-container {
        background-color: #1a1a1a !important;
        border-color: #404040 !important;
    }

    [data-theme="dark"] .message-time,
    .stApp[data-theme="dark"] .message-time,
    .message-time {
        color: #cccccc !important;
    }

    [data-theme="dark"] .media-upload-section,
    .stApp[data-theme="dark"] .media-upload-section {
        background: rgba(255,255,255,0.05) !important;
        border-color: #404040 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    if not st.session_state.is_authenticated:
        show_login_page()
        return

    with st.sidebar:
        st.markdown("### 👤 User Info")
        st.write(f"**Username:** {st.session_state.current_user}")
        st.write(f"**Role:** {'Admin' if st.session_state.is_admin else 'User'}")

        st.markdown("---")

        if st.session_state.is_admin:
            st.markdown("### 🛠 Admin Controls")

            view_options = ["📧 Inbox", "💬 Chat View"] if st.session_state.selected_user_chat else ["📧 Inbox"]
            current_view = "📧 Inbox" if st.session_state.admin_view_mode == "inbox" else "💬 Chat View"

            selected_view = st.selectbox("View Mode:", view_options, index=view_options.index(current_view))

            if selected_view == "📧 Inbox" and st.session_state.admin_view_mode != "inbox":
                st.session_state.admin_view_mode = "inbox"
                st.session_state.selected_user_chat = None
                st.rerun()

            st.markdown("### ⏰ Auto Refresh")
            st.session_state.auto_refresh_enabled = st.checkbox("Auto-refresh enabled",
                                                                st.session_state.auto_refresh_enabled)
            new_refresh_time = st.slider("Refresh interval (seconds):", 1, 30, st.session_state.auto_refresh_time)
            if new_refresh_time != st.session_state.auto_refresh_time:
                st.session_state.auto_refresh_time = new_refresh_time

            user_chats = get_all_user_chats()
            total_unread = sum(chat["unread_count"] for chat in user_chats)

            st.markdown("### 📊 Quick Stats")
            st.metric("Active Users", len(user_chats))
            st.metric("Unread Messages", total_unread)

        else:
            st.markdown("### 💬 Chat Info")
            st.info("You are chatting privately")
            st.markdown("🟢 Online")

        st.markdown("---")

        if st.button("🚪 Logout", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.success("Logged out successfully!")
            time.sleep(1)
            st.rerun()

    if st.session_state.is_admin:
        if st.session_state.admin_view_mode == "inbox":
            show_admin_inbox()
        elif st.session_state.admin_view_mode == "chat" and st.session_state.selected_user_chat:
            show_admin_chat_view()
        else:
            show_admin_inbox()
    else:
        show_user_chat_view()

    # Auto-refresh logic - always enabled for users, admin controlled for admins
    if st.session_state.auto_refresh_enabled or not st.session_state.is_admin:
        time.sleep(st.session_state.auto_refresh_time)
        st.rerun()


if __name__ == "__main__":
    main()