import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import Counter
import json
from sqlalchemy.orm import Session
from models.models import CollectionJob, RedditPost, RedditComment, Analytics

logger = logging.getLogger(__name__)

class AnalyticsService:
    """
    Advanced analytics service for Reddit data analysis
    """
    
    def __init__(self):
        pass
    
    def generate_collection_analytics(
        self,
        job_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Generate comprehensive analytics for a collection job
        
        Args:
            job_id: Collection job ID
            db: Database session
            
        Returns:
            Analytics dictionary
        """
        try:
            # Get collection job
            job = db.query(CollectionJob).filter(CollectionJob.job_id == job_id).first()
            if not job:
                raise ValueError(f"Collection job {job_id} not found")
            
            # Get all posts and comments for this job
            posts = db.query(RedditPost).filter(RedditPost.collection_job_id == job.id).all()
            comments = []
            for post in posts:
                post_comments = db.query(RedditComment).filter(RedditComment.post_id == post.id).all()
                comments.extend(post_comments)
            
            # Generate analytics
            analytics_data = {
                "summary": self._generate_summary_stats(posts, comments),
                "engagement": self._analyze_engagement(posts, comments),
                "content": self._analyze_content(posts, comments),
                "temporal": self._analyze_temporal_patterns(posts, comments),
                "users": self._analyze_user_activity(posts, comments),
                "subreddits": self._analyze_subreddit_distribution(posts)
            }
            
            # Save analytics to database
            analytics_record = Analytics(
                collection_job_id=job.id,
                total_posts=len(posts),
                total_comments=len(comments),
                total_users=len(set([p.author for p in posts if p.author] + [c.author for c in comments if c.author])),
                avg_score=sum([p.score for p in posts]) / len(posts) if posts else 0,
                avg_comments_per_post=sum([p.num_comments for p in posts]) / len(posts) if posts else 0,
                avg_upvote_ratio=sum([p.upvote_ratio for p in posts]) / len(posts) if posts else 0,
                top_posts=json.dumps(analytics_data["engagement"]["top_posts"]),
                most_commented=json.dumps(analytics_data["engagement"]["most_commented"]),
                active_users=json.dumps(analytics_data["users"]["most_active"]),
                common_keywords=json.dumps(analytics_data["content"]["common_keywords"]),
                post_type_distribution=json.dumps(analytics_data["content"]["post_types"]),
                posting_patterns=json.dumps(analytics_data["temporal"]["posting_patterns"]),
                engagement_trends=json.dumps(analytics_data["temporal"]["engagement_trends"])
            )
            
            db.add(analytics_record)
            db.commit()
            
            logger.info(f"Generated analytics for collection job {job_id}")
            return analytics_data
            
        except Exception as e:
            logger.error(f"Error generating analytics for job {job_id}: {e}")
            raise
    
    def _generate_summary_stats(
        self,
        posts: List[RedditPost],
        comments: List[RedditComment]
    ) -> Dict[str, Any]:
        """Generate summary statistics"""
        if not posts:
            return {
                "total_posts": 0,
                "total_comments": 0,
                "avg_score": 0,
                "avg_comments_per_post": 0,
                "score_range": {"min": 0, "max": 0},
                "date_range": {"earliest": None, "latest": None}
            }
        
        scores = [p.score for p in posts]
        dates = [p.created_utc for p in posts if p.created_utc]
        
        return {
            "total_posts": len(posts),
            "total_comments": len(comments),
            "avg_score": sum(scores) / len(scores),
            "avg_comments_per_post": sum([p.num_comments for p in posts]) / len(posts),
            "score_range": {
                "min": min(scores),
                "max": max(scores)
            },
            "date_range": {
                "earliest": min(dates).isoformat() if dates else None,
                "latest": max(dates).isoformat() if dates else None
            }
        }
    
    def _analyze_engagement(
        self,
        posts: List[RedditPost],
        comments: List[RedditComment]
    ) -> Dict[str, Any]:
        """Analyze engagement metrics"""
        # Sort posts by score
        top_posts = sorted(posts, key=lambda x: x.score, reverse=True)[:10]
        most_commented = sorted(posts, key=lambda x: x.num_comments, reverse=True)[:10]
        
        # Convert to serializable format
        top_posts_data = [
            {
                "title": post.title,
                "score": post.score,
                "comments": post.num_comments,
                "subreddit": post.subreddit,
                "reddit_id": post.reddit_id
            }
            for post in top_posts
        ]
        
        most_commented_data = [
            {
                "title": post.title,
                "score": post.score,
                "comments": post.num_comments,
                "subreddit": post.subreddit,
                "reddit_id": post.reddit_id
            }
            for post in most_commented
        ]
        
        return {
            "top_posts": top_posts_data,
            "most_commented": most_commented_data,
            "avg_upvote_ratio": sum([p.upvote_ratio for p in posts]) / len(posts) if posts else 0,
            "high_engagement_threshold": {
                "score": sum([p.score for p in posts]) / len(posts) * 2 if posts else 0,
                "comments": sum([p.num_comments for p in posts]) / len(posts) * 2 if posts else 0
            }
        }
    
    def _analyze_content(
        self,
        posts: List[RedditPost],
        comments: List[RedditComment]
    ) -> Dict[str, Any]:
        """Analyze content patterns"""
        # Extract keywords from titles
        all_titles = " ".join([p.title.lower() for p in posts if p.title])
        words = all_titles.split()
        # Filter out common words
        common_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are", "was", "were", "be", "been", "have", "has", "had", "do", "does", "did", "will", "would", "could", "should", "may", "might", "can", "this", "that", "these", "those", "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them", "my", "your", "his", "her", "its", "our", "their"}
        filtered_words = [word for word in words if len(word) > 2 and word not in common_words]
        word_counts = Counter(filtered_words)
        
        # Analyze post types
        post_types = Counter()
        for post in posts:
            if post.is_nsfw:
                post_types["nsfw"] += 1
            if post.post_hint:
                post_types[post.post_hint] += 1
            elif post.url and any(domain in post.url for domain in ["reddit.com", "redd.it"]):
                post_types["text"] += 1
            elif post.url:
                post_types["link"] += 1
            else:
                post_types["text"] += 1
        
        return {
            "common_keywords": dict(word_counts.most_common(20)),
            "post_types": dict(post_types),
            "avg_title_length": sum([len(p.title) for p in posts if p.title]) / len(posts) if posts else 0,
            "avg_text_length": sum([len(p.selftext or "") for p in posts]) / len(posts) if posts else 0
        }
    
    def _analyze_temporal_patterns(
        self,
        posts: List[RedditPost],
        comments: List[RedditComment]
    ) -> Dict[str, Any]:
        """Analyze temporal posting patterns"""
        if not posts:
            return {"posting_patterns": {}, "engagement_trends": {}}
        
        # Group posts by hour of day
        hour_counts = Counter()
        for post in posts:
            if post.created_utc:
                hour_counts[post.created_utc.hour] += 1
        
        # Group posts by day of week
        day_counts = Counter()
        for post in posts:
            if post.created_utc:
                day_counts[post.created_utc.strftime("%A")] += 1
        
        # Engagement over time (score trends)
        engagement_by_hour = {}
        for post in posts:
            if post.created_utc:
                hour = post.created_utc.hour
                if hour not in engagement_by_hour:
                    engagement_by_hour[hour] = []
                engagement_by_hour[hour].append(post.score)
        
        avg_engagement_by_hour = {
            hour: sum(scores) / len(scores)
            for hour, scores in engagement_by_hour.items()
        }
        
        return {
            "posting_patterns": {
                "by_hour": dict(hour_counts),
                "by_day": dict(day_counts)
            },
            "engagement_trends": {
                "avg_score_by_hour": avg_engagement_by_hour,
                "peak_posting_hour": max(hour_counts, key=hour_counts.get) if hour_counts else None,
                "peak_engagement_hour": max(avg_engagement_by_hour, key=avg_engagement_by_hour.get) if avg_engagement_by_hour else None
            }
        }
    
    def _analyze_user_activity(
        self,
        posts: List[RedditPost],
        comments: List[RedditComment]
    ) -> Dict[str, Any]:
        """Analyze user activity patterns"""
        user_stats = {}
        
        # Analyze post authors
        for post in posts:
            if post.author:
                if post.author not in user_stats:
                    user_stats[post.author] = {
                        "username": post.author,
                        "post_count": 0,
                        "comment_count": 0,
                        "total_score": 0
                    }
                user_stats[post.author]["post_count"] += 1
                user_stats[post.author]["total_score"] += post.score
        
        # Analyze comment authors
        for comment in comments:
            if comment.author:
                if comment.author not in user_stats:
                    user_stats[comment.author] = {
                        "username": comment.author,
                        "post_count": 0,
                        "comment_count": 0,
                        "total_score": 0
                    }
                user_stats[comment.author]["comment_count"] += 1
                user_stats[comment.author]["total_score"] += comment.score
        
        # Sort by total score
        most_active = sorted(
            user_stats.values(),
            key=lambda x: x["total_score"],
            reverse=True
        )[:10]
        
        return {
            "total_unique_users": len(user_stats),
            "most_active": most_active,
            "avg_posts_per_user": sum([u["post_count"] for u in user_stats.values()]) / len(user_stats) if user_stats else 0,
            "avg_comments_per_user": sum([u["comment_count"] for u in user_stats.values()]) / len(user_stats) if user_stats else 0
        }
    
    def _analyze_subreddit_distribution(
        self,
        posts: List[RedditPost]
    ) -> Dict[str, Any]:
        """Analyze subreddit distribution"""
        subreddit_counts = Counter([p.subreddit for p in posts if p.subreddit])
        subreddit_scores = {}
        
        for post in posts:
            if post.subreddit:
                if post.subreddit not in subreddit_scores:
                    subreddit_scores[post.subreddit] = []
                subreddit_scores[post.subreddit].append(post.score)
        
        avg_scores_by_subreddit = {
            sub: sum(scores) / len(scores)
            for sub, scores in subreddit_scores.items()
        }
        
        return {
            "distribution": dict(subreddit_counts),
            "avg_score_by_subreddit": avg_scores_by_subreddit,
            "most_active_subreddit": max(subreddit_counts, key=subreddit_counts.get) if subreddit_counts else None,
            "highest_scoring_subreddit": max(avg_scores_by_subreddit, key=avg_scores_by_subreddit.get) if avg_scores_by_subreddit else None
        }