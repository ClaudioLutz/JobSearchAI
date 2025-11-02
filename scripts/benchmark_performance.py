"""
Performance benchmark script for JobSearchAI database.

Measures query performance and deduplication effectiveness.
"""

import time
import statistics
import sys
import os
import json
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.db_utils import JobMatchDatabase


def benchmark_query_performance(db_path="instance/jobsearchai.db", iterations=100):
    """
    Benchmark database query performance
    
    Args:
        db_path: Path to SQLite database
        iterations: Number of iterations for each test
        
    Returns:
        dict: Performance metrics
    """
    print("\n" + "="*60)
    print("Query Performance Benchmark")
    print("="*60 + "\n")
    
    db = JobMatchDatabase(db_path)
    db.connect()
    
    if not db.conn:
        print("❌ Failed to connect to database")
        return None
    
    cursor = db.conn.cursor()
    
    # Check if we have enough data
    cursor.execute("SELECT COUNT(*) FROM job_matches")
    count = cursor.fetchone()[0]
    
    if count < 10:
        print(f"⚠️  Not enough data for benchmark (need at least 10 records, found {count})")
        db.close()
        return None
    
    print(f"📊 Database contains {count} job matches")
    print(f"🔄 Running {iterations} iterations for each test...\n")
    
    results = {}
    
    # Test 1: Single job lookup by URL
    print("Test 1: Job lookup by URL")
    cursor.execute("SELECT job_url FROM job_matches LIMIT 1")
    test_url = cursor.fetchone()[0]
    
    times = []
    for _ in range(iterations):
        start = time.time()
        cursor.execute("""
            SELECT scraped_data FROM job_matches 
            WHERE job_url = ? 
            LIMIT 1
        """, (test_url,))
        cursor.fetchone()
        elapsed = time.time() - start
        times.append(elapsed * 1000)  # Convert to ms
    
    results['single_lookup'] = {
        'avg': statistics.mean(times),
        'median': statistics.median(times),
        'p95': sorted(times)[int(len(times) * 0.95)],
        'min': min(times),
        'max': max(times)
    }
    
    print(f"  Average:  {results['single_lookup']['avg']:.2f}ms")
    print(f"  Median:   {results['single_lookup']['median']:.2f}ms")
    print(f"  P95:      {results['single_lookup']['p95']:.2f}ms")
    print(f"  Min/Max:  {results['single_lookup']['min']:.2f}ms / {results['single_lookup']['max']:.2f}ms")
    
    # Test 2: Filter by search term
    print("\nTest 2: Filter by search term")
    cursor.execute("SELECT DISTINCT search_term FROM job_matches LIMIT 1")
    row = cursor.fetchone()
    if row:
        test_term = row[0]
        
        times = []
        for _ in range(iterations):
            start = time.time()
            cursor.execute("""
                SELECT * FROM job_matches 
                WHERE search_term = ?
                LIMIT 20
            """, (test_term,))
            cursor.fetchall()
            elapsed = time.time() - start
            times.append(elapsed * 1000)
        
        results['search_term_filter'] = {
            'avg': statistics.mean(times),
            'median': statistics.median(times),
            'p95': sorted(times)[int(len(times) * 0.95)]
        }
        
        print(f"  Average:  {results['search_term_filter']['avg']:.2f}ms")
        print(f"  Median:   {results['search_term_filter']['median']:.2f}ms")
        print(f"  P95:      {results['search_term_filter']['p95']:.2f}ms")
    
    # Test 3: Filter by score
    print("\nTest 3: Filter by overall match score")
    times = []
    for _ in range(iterations):
        start = time.time()
        cursor.execute("""
            SELECT * FROM job_matches 
            WHERE overall_match >= 7
            ORDER BY overall_match DESC
            LIMIT 20
        """, ())
        cursor.fetchall()
        elapsed = time.time() - start
        times.append(elapsed * 1000)
    
    results['score_filter'] = {
        'avg': statistics.mean(times),
        'median': statistics.median(times),
        'p95': sorted(times)[int(len(times) * 0.95)]
    }
    
    print(f"  Average:  {results['score_filter']['avg']:.2f}ms")
    print(f"  Median:   {results['score_filter']['median']:.2f}ms")
    print(f"  P95:      {results['score_filter']['p95']:.2f}ms")
    
    # Test 4: Complex query (multiple filters)
    print("\nTest 4: Complex multi-filter query")
    times = []
    for _ in range(iterations):
        start = time.time()
        cursor.execute("""
            SELECT * FROM job_matches 
            WHERE overall_match >= 6
            AND location IS NOT NULL
            ORDER BY overall_match DESC, matched_at DESC
            LIMIT 10
        """, ())
        cursor.fetchall()
        elapsed = time.time() - start
        times.append(elapsed * 1000)
    
    results['complex_query'] = {
        'avg': statistics.mean(times),
        'median': statistics.median(times),
        'p95': sorted(times)[int(len(times) * 0.95)]
    }
    
    print(f"  Average:  {results['complex_query']['avg']:.2f}ms")
    print(f"  Median:   {results['complex_query']['median']:.2f}ms")
    print(f"  P95:      {results['complex_query']['p95']:.2f}ms")
    
    # Test 5: Duplicate check (exists query)
    print("\nTest 5: Duplicate existence check")
    times = []
    for _ in range(iterations):
        start = time.time()
        exists = db.job_exists(test_url, "test_search", "test_cv_key")
        elapsed = time.time() - start
        times.append(elapsed * 1000)
    
    results['duplicate_check'] = {
        'avg': statistics.mean(times),
        'median': statistics.median(times),
        'p95': sorted(times)[int(len(times) * 0.95)]
    }
    
    print(f"  Average:  {results['duplicate_check']['avg']:.2f}ms")
    print(f"  Median:   {results['duplicate_check']['median']:.2f}ms")
    print(f"  P95:      {results['duplicate_check']['p95']:.2f}ms")
    
    db.close()
    
    # Overall assessment
    print(f"\n{'='*60}")
    print("Performance Assessment")
    print(f"{'='*60}")
    
    target_ms = 100
    all_pass = True
    
    for test_name, metrics in results.items():
        p95 = metrics['p95']
        status = "✅ PASS" if p95 < target_ms else "❌ FAIL"
        if p95 >= target_ms:
            all_pass = False
        print(f"{test_name}: P95 {p95:.2f}ms - {status}")
    
    print(f"\nTarget: <{target_ms}ms (P95)")
    print(f"Overall: {'✅ ALL TESTS PASSED' if all_pass else '❌ SOME TESTS FAILED'}")
    print(f"{'='*60}\n")
    
    return results


def benchmark_deduplication_effectiveness(db_path="instance/jobsearchai.db"):
    """
    Benchmark deduplication effectiveness
    
    Args:
        db_path: Path to SQLite database
        
    Returns:
        dict: Deduplication metrics
    """
    print("\n" + "="*60)
    print("Deduplication Effectiveness Benchmark")
    print("="*60 + "\n")
    
    db = JobMatchDatabase(db_path)
    db.connect()
    
    if not db.conn:
        print("❌ Failed to connect to database")
        return None
    
    cursor = db.conn.cursor()
    
    # Total unique jobs
    cursor.execute("SELECT COUNT(DISTINCT job_url) FROM job_matches")
    unique_jobs = cursor.fetchone()[0]
    
    # Total records
    cursor.execute("SELECT COUNT(*) FROM job_matches")
    total_records = cursor.fetchone()[0]
    
    # Jobs scraped multiple times (for different searches or CVs)
    cursor.execute("""
        SELECT COUNT(*) FROM (
            SELECT job_url, COUNT(*) as count
            FROM job_matches
            GROUP BY job_url
            HAVING count > 1
        )
    """)
    multi_scraped = cursor.fetchone()[0]
    
    # Average records per unique job
    avg_per_job = total_records / unique_jobs if unique_jobs > 0 else 0
    
    # Deduplication rate
    dedup_rate = ((total_records - unique_jobs) / total_records * 100) if total_records > 0 else 0
    
    print(f"📊 Database Statistics:")
    print(f"  Total records:        {total_records}")
    print(f"  Unique jobs (URLs):   {unique_jobs}")
    print(f"  Multi-scraped jobs:   {multi_scraped}")
    print(f"  Avg records per job:  {avg_per_job:.2f}")
    print(f"  Deduplication rate:   {dedup_rate:.1f}%")
    
    # Search term diversity
    cursor.execute("SELECT COUNT(DISTINCT search_term) FROM job_matches")
    unique_terms = cursor.fetchone()[0]
    
    print(f"\n📊 Search Diversity:")
    print(f"  Unique search terms:  {unique_terms}")
    
    # CV key diversity
    cursor.execute("SELECT COUNT(DISTINCT cv_key) FROM job_matches")
    unique_cvs = cursor.fetchone()[0]
    
    print(f"  Unique CV versions:   {unique_cvs}")
    
    # Scrape history analysis
    cursor.execute("SELECT COUNT(*) FROM scrape_history")
    scrape_count = cursor.fetchone()[0]
    
    if scrape_count > 0:
        cursor.execute("""
            SELECT 
                SUM(jobs_found) as total_found,
                SUM(new_jobs) as total_new,
                SUM(duplicate_jobs) as total_dupes
            FROM scrape_history
        """)
        row = cursor.fetchone()
        if row and row[0]:
            total_found, total_new, total_dupes = row
            
            print(f"\n📊 Scrape History ({scrape_count} scrapes):")
            print(f"  Total jobs found:     {total_found}")
            print(f"  New jobs added:       {total_new}")
            print(f"  Duplicates skipped:   {total_dupes}")
            
            if total_found > 0:
                skip_rate = (total_dupes / total_found * 100)
                print(f"  Skip rate:            {skip_rate:.1f}%")
                
                estimated_api_savings = total_dupes  # Each duplicate = 1 saved API call
                print(f"\n💰 Estimated Savings:")
                print(f"  API calls saved:      {estimated_api_savings}")
                print(f"  Cost savings:         ${estimated_api_savings * 0.01:.2f} (@ $0.01/call)")
    
    db.close()
    
    print(f"\n{'='*60}\n")
    
    return {
        'total_records': total_records,
        'unique_jobs': unique_jobs,
        'dedup_rate': dedup_rate,
        'unique_search_terms': unique_terms,
        'unique_cv_versions': unique_cvs
    }


def save_benchmark_results(query_results, dedup_results, output_file):
    """
    Save benchmark results to JSON file
    
    Args:
        query_results: Query performance results
        dedup_results: Deduplication effectiveness results
        output_file: Path to output file
    """
    results = {
        'timestamp': datetime.now().isoformat(),
        'query_performance': query_results,
        'deduplication': dedup_results
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    print(f"📄 Results saved to: {output_file}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Benchmark database performance and deduplication effectiveness',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full benchmark
  python scripts/benchmark_performance.py
  
  # Custom iteration count
  python scripts/benchmark_performance.py --iterations 200
  
  # Save results to file
  python scripts/benchmark_performance.py --output benchmarks/results_20251102.json
        """
    )
    
    parser.add_argument(
        '--db-path',
        default='instance/jobsearchai.db',
        help='Path to SQLite database (default: instance/jobsearchai.db)'
    )
    
    parser.add_argument(
        '--iterations',
        type=int,
        default=100,
        help='Number of iterations for query tests (default: 100)'
    )
    
    parser.add_argument(
        '--output',
        help='Output file for results (JSON format)'
    )
    
    parser.add_argument(
        '--query-only',
        action='store_true',
        help='Run only query performance tests'
    )
    
    parser.add_argument(
        '--dedup-only',
        action='store_true',
        help='Run only deduplication effectiveness tests'
    )
    
    args = parser.parse_args()
    
    try:
        query_results = None
        dedup_results = None
        
        if not args.dedup_only:
            query_results = benchmark_query_performance(args.db_path, args.iterations)
        
        if not args.query_only:
            dedup_results = benchmark_deduplication_effectiveness(args.db_path)
        
        if args.output and (query_results or dedup_results):
            # Create benchmarks directory if it doesn't exist
            output_dir = os.path.dirname(args.output)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            save_benchmark_results(query_results, dedup_results, args.output)
        
        # Exit with success if all query tests passed (when run)
        if query_results:
            all_pass = all(
                metrics['p95'] < 100 
                for metrics in query_results.values()
            )
            sys.exit(0 if all_pass else 1)
        else:
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Benchmark interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
