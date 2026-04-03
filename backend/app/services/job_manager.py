from typing import Dict, Optional
from datetime import datetime
from queue import Queue
from app.models import JobStatus, AuthAnalysis

class JobManager:
    """
    Manages analysis jobs with in-memory storage.
    Tracks job status, progress, and results.
    """
    
    def __init__(self):
        self.jobs: Dict[str, JobStatus] = {}
        self.event_queues: Dict[str, Queue] = {}
    
    def create_job(self, job_id: str, url: str) -> JobStatus:
        """Create a new analysis job"""
        now = datetime.now()
        job = JobStatus(
            job_id=job_id,
            status="pending",
            progress=0,
            stage="initializing",
            result=None,
            error=None,
            created_at=now,
            updated_at=now
        )
        self.jobs[job_id] = job
        self.event_queues[job_id] = Queue()
        return job
    
    def get_job(self, job_id: str) -> Optional[JobStatus]:
        """Get job status by ID"""
        return self.jobs.get(job_id)
    
    def update_job(self, job_id: str, updates: dict):
        """Update job with new data"""
        if job_id in self.jobs:
            job = self.jobs[job_id]
            
            # Update fields
            if 'status' in updates:
                job.status = updates['status']
            if 'progress' in updates:
                job.progress = updates['progress']
            if 'stage' in updates:
                job.stage = updates['stage']
            if 'result' in updates:
                job.result = updates['result']
            if 'error' in updates:
                job.error = updates['error']
            
            job.updated_at = datetime.now()
            self.jobs[job_id] = job
    
    def complete_job(self, job_id: str, result: AuthAnalysis):
        """Mark job as completed with result"""
        self.update_job(job_id, {
            'status': 'completed',
            'progress': 100,
            'stage': 'complete',
            'result': result
        })
    
    def fail_job(self, job_id: str, error: str):
        """Mark job as failed with error message"""
        self.update_job(job_id, {
            'status': 'failed',
            'progress': 0,
            'error': error
        })
    
    def get_event_queue(self, job_id: str) -> Optional[Queue]:
        """Get event queue for streaming"""
        return self.event_queues.get(job_id)
    
    def cleanup_old_jobs(self, max_age_hours: int = 24):
        """Remove jobs older than max_age_hours"""
        now = datetime.now()
        to_remove = []
        
        for job_id, job in self.jobs.items():
            age = (now - job.created_at).total_seconds() / 3600
            if age > max_age_hours:
                to_remove.append(job_id)
        
        for job_id in to_remove:
            del self.jobs[job_id]
            if job_id in self.event_queues:
                del self.event_queues[job_id]
        
        return len(to_remove)

# Global job manager instance
job_manager = JobManager()
