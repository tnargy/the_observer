Guidelines.md

This PRD is designed for shipping, not perfection:
✅ Much shorter (Phase 1 only, ~2k words vs 15k)
✅ Copy-paste code (pseudocode for agent, collector, dashboard components)
✅ Week-by-week breakdown (exactly what to build each week)
✅ No overkill (no TLS, no fancy auth, no rate limiting, no enterprise paranoia)
✅ Honest about pain (lists what will be annoying + tells you to ignore it)
✅ Honest about scope (what's in Phase 1, what's Phase 2)
✅ Real timelines (8 weeks, not 16)
✅ Success criteria (you know you're done when...)
Key Differences from the "Business PRD"
AspectBusiness PRDVibe PRDAuthPer-agent API keys, hashingHardcoded username/passwordTLSMandatory, certificate pinningSelf-signed cert, no verifyInput validationJSON schema, detailed"Is it JSON?"Error handlingGraceful, with fallbacksIt crashed? Restart itRate limitingPer-agent limitsNo limits neededLoggingStructured JSON, audit trailPrint to consoleScalability2-50 agents, tested"Works for my 5 machines"MonitoringPrometheus metrics, health checksJust works or it doesn'tDocs50+ pagesREADME + setup guide
How to Use This

Read it this week (30 min, skim the whole thing)
Pick start date (Monday is good)
Follow Week 1 (setup + planning)
Week 2: Start coding the agent
Weeks 3-8: Follow the breakdown, ship incrementally
Week 8: You have a working system

Three Things to Remember

Scope cuts are your friend. If something feels hard or boring, punt it to Phase 2. Seriously. The goal is to finish and learn, not to build perfection.
Deploy real early. Week 7, not week 15. Get it running on an actual machine. That's when the magic happens—you see it working for real.
You're building for you. The only user is you. Build what makes you happy. Want to monitor your gaming PC? Cool. Your Raspberry Pi? Perfect. The server in your closet? Ideal. This is the freedom of personal projects.


How to Use PRD + TRD Together
PRD (Observer_Phase1_VibeCodePRD.md):

Read this first (overview, timeline, scope)
30 min read
Answers: "What am I building and why?"

TRD (Observer_Phase1_TRD.md):

Keep open while coding
Reference when you need details
Answers: "What should this return?" and "How do I structure this?"

Example workflow:

Week 2 - Agent:

Read PRD Week 2 section (what to build)
Open TRD Section 1 (Agent Specifications)
Copy the code patterns, adapt for your machine


Week 5 - Dashboard:

Read PRD Week 5 section
Open TRD Section 5 (React Components)
Copy the component structure, fill in details

Scope.md

Phase 1 (The Real MVP, 2–3 months):

Agent: Collect CPU, RAM, Disk, Network (just those 4)
Collector: Flask endpoint, PostgreSQL, in-memory registry
Dashboard: Server cards + 1-hour line chart for details
Auth: Basic (hardcoded username/password, no fancy RBAC)
Thresholds: Simple (90% CPU = red, that's it)
WebSocket: Works, broadcasts updates, that's it
Docs: README, 15-minute setup guide
Deploy: Docker Compose file

That's enough to learn everything and have a working system.
Phase 2 (If You're Still Having Fun, 1–2 months):

Add email alerts
Add multi-user auth
Add Redis caching
Add systemd templates
Add backup/restore docs


Timeline.md

This week:

Read Flask + React tutorials (refresh your memory, 3–4 hours)
Sketch agent/collector/dashboard on paper (30 min)
Create GitHub repo, write simple README (30 min)


Next week:

Start agent: Just collect CPU & RAM using psutil, print to console
Get that working in isolation (no HTTP yet)


Week 3:

Add HTTP POST to Flask dummy endpoint
Flask just prints what it receives (no DB yet)


Week 4:

Add PostgreSQL, store metrics
Query metrics from database


Week 5:

Add React dashboard, fetch metrics from API
Display as table (no charts yet)


Week 6:

Add Recharts line chart
Add WebSocket (basic broadcast)


Week 7:

Polish, fix bugs, Docker Compose


Week 8:

Deploy to real server
Write docs
Ship it
