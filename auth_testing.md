## Auth-Gated App Testing Playbook

### Step 1: Create Test User & Session
```
mongosh --eval "
use('conceptforge_db');
var userId = 'test-user-' + Date.now();
var sessionToken = 'test_session_' + Date.now();
db.users.insertOne({
  id: userId,
  email: 'test.user.' + Date.now() + '@example.com',
  name: 'Test User',
  picture: 'https://via.placeholder.com/150',
  role: 'user',
  created_at: new Date().toISOString()
});
db.user_sessions.insertOne({
  user_id: userId,
  session_token: sessionToken,
  expires_at: new Date(Date.now() + 7*24*60*60*1000),
  created_at: new Date()
});
print('Session token: ' + sessionToken);
print('User ID: ' + userId);
"
```

### Step 2: Test Backend API
- GET /api/auth/me with session_token in cookie OR Authorization: Bearer <session_token>
- Should return the user document (id, email, name, picture, role)

### Step 3: Browser Testing
```
await page.context.add_cookies([{
    "name": "session_token",
    "value": "YOUR_SESSION_TOKEN",
    "domain": "study-path-gen.preview.emergentagent.com",
    "path": "/",
    "httpOnly": True,
    "secure": True,
    "sameSite": "None"
}])
await page.goto("https://study-path-gen.preview.emergentagent.com/app")
```

### Checklist
- [x] users collection uses `id` field (UUID). `_id` is projected out.
- [x] user_sessions.user_id matches users.id exactly.
- [x] All queries use `{"_id": 0}` projection.
- [x] Backend accepts session_token from cookie OR Bearer header.
- [x] Backend also still accepts legacy JWT `access_token` cookie / Bearer (email-password users).

### Success indicators
- `/api/auth/me` returns user data
- Dashboard loads without redirect
- CRUD operations work
