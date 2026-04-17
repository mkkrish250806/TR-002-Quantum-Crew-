# Integration Testing Guide

## 🧪 Before You Start

Make sure you have:
- ✅ Backend running on `http://127.0.0.1:8000`
- ✅ Frontend running on `http://localhost:5173`
- ✅ Both services are accessible from your browser

## 🔍 Testing the API Connection

### Test 1: Backend Health Check

**Method**: GET
**URL**: `http://127.0.0.1:8000/`

**Via cURL**:
```bash
curl http://127.0.0.1:8000/
```

**Expected Response**:
```json
{
  "status": "ok",
  "service": "healthcare-rag-support"
}
```

**Via Browser Console**:
```javascript
fetch('http://127.0.0.1:8000/')
  .then(r => r.json())
  .then(console.log)
  .catch(console.error)
```

### Test 2: Send Chat Message

**Method**: POST
**URL**: `http://127.0.0.1:8000/chat`

**Request Body**:
```json
{
  "message": "I have a headache and mild fever",
  "session_id": "test_session_001"
}
```

**Via cURL**:
```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I have a headache and mild fever",
    "session_id": "test_session_001"
  }'
```

**Expected Response**:
```json
{
  "answer": "Based on your symptoms...",
  "intent": "symptom_inquiry",
  "confidence": 0.92,
  "urgency": "medium",
  "emotion": "concerned",
  "resolved": false,
  "sources": ["Medical Knowledge Base"],
  "booking_status": "none",
  "booking_id": "",
  "booked_slot": "",
  "booked_department": "",
  "patient_name": ""
}
```

### Test 3: Get Metrics

**Method**: GET
**URL**: `http://127.0.0.1:8000/metrics`

**Via cURL**:
```bash
curl http://127.0.0.1:8000/metrics
```

**Expected Response**:
```json
{
  "resolution_rate": 78,
  "total_queries": 45,
  "resolved_queries": 35,
  "emergency_cases_flagged": 2
}
```

## 🎯 Testing in Frontend

### Test 1: API Health Check on Startup

**Steps**:
1. Open DevTools (F12)
2. Go to Console tab
3. Refresh the page
4. Look for messages like:
   - ✅ "API Health Check: Connected"
   - ❌ "API Health Check: Failed"

**What to see**:
- Green connection indicator in header
- "🟢 Connected" status
- Chat is enabled

### Test 2: Send a Test Message

**Steps**:
1. Type in chat: "What is diabetes?"
2. Click Send or press Enter
3. Observe:
   - Message appears in blue
   - Typing indicator shows
   - Response appears in gray/white
   - Metadata panel shows below response

**Check for**:
- ✅ Intent: keyword classification
- ✅ Confidence: 0-100% score
- ✅ Urgency: Low/Medium/High
- ✅ Sources: Knowledge base references

### Test 3: Test Error Handling

**Steps**:
1. Stop backend (Ctrl+C)
2. Try to send a message in frontend
3. Observe error handling:
   - Red error message appears
   - Helpful guidance is shown
   - UI doesn't crash

**Expected behavior**:
- Graceful error message
- "Connection Issue" notice on startup
- Clear instructions to restart backend

### Test 4: Test Session Persistence

**Steps**:
1. Send a message
2. Refresh the page
3. Previous message should reappear
4. Continue conversation

**Expected behavior**:
- Messages persist across refresh
- Session ID remains same
- Can restore conversation

### Test 5: Test Responsiveness

**Desktop View**:
- Dashboard on left
- Chat on right
- Footer at bottom

**Tablet View (800px)**:
- Dashboard on left
- Chat takes more space
- Footer responsive

**Mobile View (400px)**:
- Single column layout
- Full-width components
- Bottom input
- Touch-friendly buttons

## 📊 Frontend Console Tests

Open DevTools console and run:

### Check API Configuration
```javascript
console.log('API Base:', import.meta.env.VITE_API_URL);
```

### Test Direct API Call
```javascript
const testMessage = async () => {
  try {
    const response = await fetch('http://127.0.0.1:8000/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: 'Test message',
        session_id: 'test_123'
      })
    });
    const data = await response.json();
    console.log('Response:', data);
    return data;
  } catch (err) {
    console.error('Error:', err);
  }
};

testMessage();
```

### Check Session Storage
```javascript
// Get stored messages
sessionStorage.getItem('healthcare_support_messages_session_123');

// Get session ID
sessionStorage.getItem('healthcare_support_session_id');

// Clear all data
sessionStorage.clear();
```

## 🔧 Troubleshooting Tests

### Issue: "Connection refused"

**Test**:
```bash
# Check if port 8000 is in use
netstat -an | grep 8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows
```

**Fix**:
```bash
# Kill process on port 8000
lsof -ti :8000 | xargs kill -9  # macOS/Linux
netstat -ano | findstr :8000 | findstr LISTENING  # Windows - note PID, then:
taskkill /PID <PID> /F
```

### Issue: "CORS error"

**Test**:
```javascript
// Check CORS headers
fetch('http://127.0.0.1:8000/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ message: 'test', session_id: 'test' })
})
.then(r => {
  console.log('Response Headers:', r.headers);
  return r.json();
})
.then(console.log);
```

**Fix**:
- Verify CORS middleware is enabled in FastAPI
- Ensure `allow_origins=["*"]` or specific origins

### Issue: "Timeout errors"

**Test**:
```javascript
// Simulate slow request
const slowTest = async () => {
  try {
    const response = await Promise.race([
      fetch('http://127.0.0.1:8000/chat', {
        method: 'POST',
        body: JSON.stringify({ message: 'test', session_id: 'test' })
      }),
      new Promise((_, reject) => 
        setTimeout(() => reject(new Error('Timeout')), 15000)
      )
    ]);
    return await response.json();
  } catch (err) {
    console.error('Timeout occurred:', err);
  }
};

slowTest();
```

### Issue: "Empty responses"

**Test**:
```bash
# Check backend logs for errors
# Terminal where backend is running should show request logs

# Test with curl for detailed response
curl -v -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Test",
    "session_id": "test_123"
  }' 2>&1 | head -50
```

## ✅ Integration Checklist

- [ ] Backend starts without errors
- [ ] Frontend loads without errors
- [ ] API health check passes
- [ ] Can send and receive messages
- [ ] Metadata displays correctly
- [ ] Dashboard metrics update
- [ ] Error handling works
- [ ] Session persistence works
- [ ] Responsive design works on mobile
- [ ] Copy-to-clipboard works
- [ ] Clear button works
- [ ] Typing indicators show
- [ ] Animations are smooth
- [ ] No console errors in DevTools

## 🎬 Test Scenarios

### Scenario A: Quick Test
1. Send: "What is diabetes?"
2. Check response appears
3. Verify metadata shows
4. ✅ Integration working

### Scenario B: Error Recovery
1. Stop backend
2. Try to send message
3. See error message
4. Restart backend
5. Message should work again
6. ✅ Error handling working

### Scenario C: Load Testing
1. Send 10 messages rapidly
2. All should process without crashing
3. UI should remain responsive
4. ✅ Performance adequate

### Scenario D: Real Conversation
1. Ask: "I have severe chest pain"
2. Check urgency = "high"
3. Ask follow-up: "For how long?"
4. Verify session_id consistent
5. ✅ Real usage working

## 📝 Logging Tips

### Frontend Logging
```javascript
// Enable in browser console
localStorage.setItem('debug', '*');
location.reload();

// Check sent requests
const originalFetch = window.fetch;
window.fetch = function(...args) {
  console.log('Fetch:', args);
  return originalFetch.apply(this, args);
};
```

### Backend Logging
```python
# In FastAPI main.py
import logging
logging.basicConfig(level=logging.DEBUG)

# Check logs in terminal where uvicorn is running
```

## 🚀 Next Steps

Once integration tests pass:
1. ✅ Deploy frontend
2. ✅ Deploy backend
3. ✅ Update API URL in production
4. ✅ Monitor system performance
5. ✅ Gather user feedback

---

**Test Coverage**: Core functionality
**Last Updated**: April 2024
