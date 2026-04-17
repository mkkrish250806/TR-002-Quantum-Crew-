# MediAssist AI - Quick Reference Card

## 🚀 Quick Start (30 seconds)

### Windows
```batch
# Navigate to project root
cd srmhack-main

# Run the startup script
start.bat
```

### macOS/Linux
```bash
# Navigate to project root
cd srmhack-main

# Make script executable
chmod +x start.sh

# Run the startup script
./start.sh
```

## 🌐 Access Points
| Service | URL | Port |
|---------|-----|------|
| Frontend | http://localhost:5173 | 5173 |
| Backend | http://127.0.0.1:8000 | 8000 |
| API Docs | http://127.0.0.1:8000/docs | 8000 |

## 📱 What You'll See

```
┌─────────────────────────────────────────────────────┐
│  🏥 MediAssist AI - Intelligent Clinical Support   │
│                                                     │
│  [🟢 Connected] [Session ABC123]                   │
├─────────────────────────────────────────────────────┤
│  Left Sidebar          │      Chat Interface        │
│  ───────────────────   │      ───────────────────   │
│  📊 Metrics:           │      💬 Healthcare AI Chat │
│  • Resolution: 85%     │                           │
│  • Total Queries: 150  │      User: Hi, help!      │
│  • Resolved: 128       │      AI: I can help...    │
│  • Urgent Cases: 12    │                           │
│                        │      [Type message...]    │
│  🔧 System Status:     │      [Send] [Clear] [🔄]  │
│  ✓ API: Active         │                           │
│  ✓ DB: Online          │                           │
│  ✓ LLM: Ready          │                           │
│  ✓ Embeddings: OK      │                           │
└─────────────────────────────────────────────────────┘
```

## 🎯 Main Features

| Feature | Location | What It Does |
|---------|----------|--------------|
| Health Check | Header | Shows 🟢 green if backend is working |
| Chat | Center | Send messages and get AI responses |
| Metrics | Left Panel | Real-time dashboard statistics |
| Metadata | Below messages | Intent, urgency, confidence scores |
| Copy | Message hover | Copy response text to clipboard |
| Clear | Input bar | Clear all messages and start fresh |
| Footer | Bottom | Links to docs, legal, social media |

## 💬 Try These Commands

### Test 1: Symptom Check
```
Type: "I have a persistent headache"
See: Urgency level, confidence score, recommendations
```

### Test 2: Appointment
```
Type: "I need to book an appointment"
See: Booking status, available slots
```

### Test 3: General Query
```
Type: "What are the symptoms of diabetes?"
See: Medical information, confidence, sources
```

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| Can't connect | Ensure backend runs on port 8000 |
| Empty responses | Check backend logs for errors |
| Slow responses | Wait 5-10 seconds on first request |
| Session lost | Messages auto-save in browser |
| Port in use | Kill process: `lsof -ti :8000 \| xargs kill -9` |

## 📊 Understanding the Response

```json
{
  "answer": "Your response text here",
  "intent": "symptom_inquiry",           // What user asked
  "urgency": "medium",                   // Low/Medium/High
  "confidence": 0.92,                    // 92% confident (0-1)
  "emotion": "concerned",                // Detected emotion
  "resolved": false,                     // Is issue resolved?
  "sources": ["Medical KB"],             // Where answer came from
  "booking_status": "available",         // Appointment status
  "patient_name": "John Doe"            // If available
}
```

## 🎨 Color Guide

| Color | Meaning |
|-------|---------|
| 🟢 Green | Good, active, resolved |
| 🟡 Yellow | Medium urgency |
| 🔴 Red | High urgency, error |
| 🔵 Blue | Information, primary action |
| ⚪ White | Normal text, neutral |

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Enter | Send message |
| Escape | Clear input |
| F12 | Open DevTools |
| Ctrl+R / Cmd+R | Refresh page |

## 📈 Performance Metrics

| Metric | Expected |
|--------|----------|
| API Response | < 2 seconds |
| Page Load | < 3 seconds |
| Message Display | < 100ms |
| Animation Frame Rate | 60 FPS |
| Memory Usage | < 50MB |

## 🔐 Security Notes

- ✅ CORS enabled for safe cross-origin requests
- ✅ Session IDs are unique per browser
- ✅ No credentials stored client-side
- ✅ All data encrypted in transit (use HTTPS in production)
- ✅ Medical data handled securely

## 📚 Documentation Files

```
srmhack-main/
├── SETUP.md              ← Installation & configuration
├── FEATURES.md           ← Architecture & features
├── TESTING.md            ← Integration tests
├── IMPLEMENTATION_SUMMARY.md ← What was built
├── README.md             ← Original project info
├── start.sh              ← macOS/Linux startup
└── start.bat             ← Windows startup
```

## 🚢 Deployment Checklist

- [ ] Backend running stably
- [ ] Frontend loads without errors
- [ ] All API endpoints working
- [ ] Metrics updating correctly
- [ ] Error handling tested
- [ ] Responsive design verified
- [ ] HTTPS configured (production)
- [ ] Environment variables set
- [ ] Database backed up
- [ ] Monitoring enabled

## 🆘 Getting Help

### Check These Files:
1. **Setup issues?** → Read `SETUP.md`
2. **Want to understand?** → Read `FEATURES.md`
3. **Testing?** → Follow `TESTING.md`
4. **Implementation details?** → See `IMPLEMENTATION_SUMMARY.md`

### Quick Diagnostics:
```bash
# Check backend
curl http://127.0.0.1:8000/

# Check metrics
curl http://127.0.0.1:8000/metrics

# Test message sending
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "test", "session_id": "test_123"}'
```

## ⏱️ Typical Session

1. **Open App** (5 sec)
   - See health check indicator
   - Dashboard loads with metrics

2. **Type Message** (3 sec)
   - Auto-complete suggests
   - Focus on input field

3. **Send & Wait** (2-5 sec)
   - See typing indicator
   - AI processing visible

4. **Receive Response** (1 sec)
   - Message appears
   - Metadata shows below
   - Metrics update

5. **Continue Conversation** (Repeat)
   - Messages persist
   - Session maintained
   - History saved

## 💡 Pro Tips

- 💡 Type descriptive symptoms for better responses
- 💡 Urgent cases get flagged with 🚨 emoji
- 💡 Look at confidence scores to gauge accuracy
- 💡 Use Copy button to save important info
- 💡 Clear button resets everything safely
- 💡 Check footer for documentation links
- 💡 Mobile view is optimized for touch
- 💡 Refresh doesn't lose chat history

## 🎓 Learning Path

1. **Beginner**: Just use the app, send messages
2. **Intermediate**: Read `FEATURES.md`, understand architecture
3. **Advanced**: Check `TESTING.md`, run diagnostics
4. **Expert**: Review code in `src/` folder

## 🔄 Maintenance

### Daily
- Monitor error logs
- Check metrics dashboard
- Verify API uptime

### Weekly
- Review performance metrics
- Check for updates
- Backup important data

### Monthly
- Security audit
- Performance optimization
- User feedback review

---

**Version**: 1.0.0
**Last Updated**: April 2024
**Status**: 🟢 Production Ready
