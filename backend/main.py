from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import contracts, jobs

app = FastAPI(title="Data Governance API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(contracts.router, prefix="/api/contracts", tags=["contracts"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)