"""
Shared HTML/CSS templates for chat messages used by the RAG apps.

Avatar images are inline SVG data-URIs so no external URL can rot.
"""

# Bot avatar: simple robot glyph (blue tones)
_BOT_SVG_B64 = (
    "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA2NCA2N"
    "CI+PGNpcmNsZSBjeD0iMzIiIGN5PSIzMiIgcj0iMjgiIGZpbGw9IiM2ZWE2ZTgiLz48cmVjdCB4"
    "PSIyMCIgeT0iMjIiIHdpZHRoPSIyNCIgaGVpZ2h0PSIyMCIgcng9IjMiIGZpbGw9IndoaXRlIiBm"
    "aWxsLW9wYWNpdHk9Ii45Ii8+PGNpcmNsZSBjeD0iMjYiIGN5PSIzMCIgcj0iMyIgZmlsbD0iIzIy"
    "NTVhYSIvPjxjaXJjbGUgY3g9IjM4IiBjeT0iMzAiIHI9IjMiIGZpbGw9IiMyMjU1YWEiLz48cmVj"
    "dCB4PSIyNiIgeT0iMzYiIHdpZHRoPSIxMiIgaGVpZ2h0PSIyIiByeD0iMSIgZmlsbD0iIzIyNTVh"
    "YSIvPjxyZWN0IHg9IjMwIiB5PSIxNiIgd2lkdGg9IjQiIGhlaWdodD0iNiIgZmlsbD0iIzZlYTZl"
    "OCIvPjxjaXJjbGUgY3g9IjMyIiBjeT0iMTQiIHI9IjMiIGZpbGw9IiM2ZWE2ZTgiLz48L3N2Zz4="
)

# User avatar: simple person glyph (pink tones)
_USER_SVG_B64 = (
    "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA2NCA2N"
    "CI+PGNpcmNsZSBjeD0iMzIiIGN5PSIzMiIgcj0iMjgiIGZpbGw9IiNlODZlYTYiLz48Y2lyY2xl"
    "IGN4PSIzMiIgY3k9IjI0IiByPSIxMCIgZmlsbD0id2hpdGUiIGZpbGwtb3BhY2l0eT0iLjkiLz48"
    "ZWxsaXBzZSBjeD0iMzIiIGN5PSI0OCIgcng9IjE2IiByeT0iMTAiIGZpbGw9IndoaXRlIiBmaWxs"
    "LW9wYWNpdHk9Ii45Ii8+PC9zdmc+"
)

_BOT_AVATAR = f"data:image/svg+xml;base64,{_BOT_SVG_B64}"
_USER_AVATAR = f"data:image/svg+xml;base64,{_USER_SVG_B64}"

css = '''
<style>
.chat-message {
    padding: 1.5rem; border-radius: 0.5rem; margin-bottom: 1rem; display: flex
}
.chat-message.user {
    background-color: #2b313e
}
.chat-message.bot {
    background-color: #475063
}
.chat-message .avatar {
  width: 20%;
}
.chat-message .avatar img {
  max-width: 78px;
  max-height: 78px;
  border-radius: 50%;
  object-fit: cover;
}
.chat-message .message {
  width: 80%;
  padding: 0 1.5rem;
  color: #fff;
}
'''

bot_template = f'''
<div class="chat-message bot">
    <div class="avatar">
        <img src="{_BOT_AVATAR}" style="max-height: 78px; max-width: 78px; border-radius: 50%; object-fit: cover;">
    </div>
    <div class="message">{{{{MSG}}}}</div>
</div>
'''

user_template = f'''
<div class="chat-message user">
    <div class="avatar">
        <img src="{_USER_AVATAR}" style="max-height: 78px; max-width: 78px; border-radius: 50%; object-fit: cover;">
    </div>
    <div class="message">{{{{MSG}}}}</div>
</div>
'''
