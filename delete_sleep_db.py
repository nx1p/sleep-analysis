import asyncio
import asyncpg

async def delete_sleep_database():
    # Connection details
    host = "192.168.0.52"
    user = "postgres"
    password = "dev_password"
    
    # Connect to the default 'postgres' database
    conn = await asyncpg.connect(
        host=host,
        user=user,
        password=password,
        database="postgres"
    )
    
    try:
        # Check if the database exists
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", "sleep_data")
        
        if exists:
            # Terminate all connections to the sleep_data database
            await conn.execute("""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = 'sleep_data'
                AND pid <> pg_backend_pid();
            """)
            
            # Drop the database
            await conn.execute("DROP DATABASE sleep_data")
            print("sleep_data database has been successfully deleted.")
        else:
            print("sleep_data database does not exist.")
    
    finally:
        # Close the connection
        await conn.close()

async def main():
    await delete_sleep_database()

if __name__ == "__main__":
    asyncio.run(main())
