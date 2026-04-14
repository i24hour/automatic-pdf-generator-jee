# Implement GitHub Connector & Commit Gamification

The goal is to allow a user to connect their GitHub profile so that they can earn +10 "points" on your platform for every Git commit they make. This creates an engaging gamification loop for developers on your platform.

## Architecture & Implementation Spec

---

### 1. Database Schema Updates (`User.ts`)
We extended the `UserSchema` to store:
- `points`: (Number, default 0) to store the total points earned.
- `githubId`: (String) the user's GitHub ID.
- `githubUsername`: (String) the user's GitHub handle.
- `githubAccessToken`: (String) to authenticate API requests on their behalf.
- `lastGithubSyncAt`: (Date) tracks the last time we synced their commits so we don't accidentally double-count them.

### 2. Authentication Updates (`nextauth/route.ts`)
- Added `GithubProvider` from `next-auth/providers/github`.
- Updated the `jwt` and `session` callbacks explicitly so that when a user logs in via GitHub, we capture their `account.access_token` and `profile.login` (their GitHub username).
- Since NextAuth natively links accounts based on email, users logging in via GitHub who already have a Google account under the same email will be seamlessly linked.

### 3. Commit Polling & Synchronization Engine (`/api/user/sync-github/route.ts`)
- **Functionality**:
  1. Finds the authenticated user in the database.
  2. Extracts the `githubUsername`.
  3. Queries GitHub official REST API: `https://api.github.com/users/{username}/events/public`.
  4. Filters for `PushEvent` types that occurred *after* the user's `lastGithubSyncAt` date (or within the last 7 days if never synced).
  5. Counts the number of commits across those pushes.
  6. Calculates `newCommits * 10`.
  7. Updates MongoDB using `$inc: { points: newCommits * 10 }` and updates `lastGithubSyncAt` to `now`.
  8. Returns the new points total to the client.

### 4. Integration
You will need to run the `sync-github` API periodically or trigger it manually from a UI action (like a "Refresh Points" button on the user's profile).

## Setup Required
1. Go to **GitHub Developer Settings** -> OAuth Apps -> New OAuth App.
2. Set Authorization callback URL to: `http://localhost:3000/api/auth/callback/github` (and your production URL).
3. Copy the Client ID and Secret and add them to your `.env` file:
   ```env
   GITHUB_CLIENT_ID=your_id_here
   GITHUB_CLIENT_SECRET=your_secret_here
   ```
