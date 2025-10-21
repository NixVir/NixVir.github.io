# Managing Blog Posts - Archive Process

## How Blog Posts Work

### Current Setup
- **Homepage displays**: 3 most recent posts (configured in `config.toml`)
- **Active posts location**: `content/post/`
- **Archived posts location**: `content/post-archive/`

### Automatic Behavior
✅ Hugo automatically shows the 3 most recent posts from `content/post/` on your homepage
✅ Posts are sorted by date (newest first)
✅ Posts in `content/post-archive/` do NOT appear on the homepage
✅ Archived posts are still accessible via their direct URL

---

## How to Archive Old Posts

When you want to make room for new content on the homepage, move older posts to the archive folder.

### Manual Method (Recommended)

**Step 1: Identify posts to archive**
```bash
# List all active posts by date
ls -lt content/post/*.md
```

**Step 2: Move old post to archive**
```bash
# Example: Archive a specific post
git mv content/post/old-post.md content/post-archive/old-post.md

# Commit the change
git add -A
git commit -m "Archive old blog post: [post title]"
git push
```

### Using R/blogdown

If you're working in RStudio:

```r
# List current posts
list.files("content/post", pattern = "*.md")

# Move to archive (example)
file.rename(
  "content/post/2019-04-17-first-post.md",
  "content/post-archive/2019-04-17-first-post.md"
)

# Commit with git
system("git add -A")
system('git commit -m "Archive old post"')
system("git push")
```

---

## Recommended Archive Strategy

### When to Archive

**Keep in active posts**:
- 3-5 most recent posts
- Posts from the last 6-12 months
- Evergreen content you want prominently displayed

**Move to archive**:
- Posts older than 1 year
- Outdated content (like the 2020 COVID posts)
- Seasonal content that's no longer relevant

### Current Status

**Active Posts (content/post/)**:
- Generational Spending Trends (2025-10-21) ✅ Current, on homepage

**Archived Posts (content/post-archive/)**:
- Financial Distress and COVID-19 Infections (2020-04-10) ✅ Archived

---

## Quick Commands

### List Active Posts
```bash
ls -lh content/post/*.md
```

### List Archived Posts
```bash
ls -lh content/post-archive/*.md
```

### Archive a Post
```bash
# Replace [filename] with actual filename
git mv content/post/[filename].md content/post-archive/[filename].md
git commit -m "Archive post: [post title]"
git push
```

### Unarchive a Post (bring back to homepage)
```bash
# Replace [filename] with actual filename
git mv content/post-archive/[filename].md content/post/[filename].md
git commit -m "Restore post: [post title]"
git push
```

---

## Creating New Posts

### Using R/blogdown (Recommended)
```r
library(blogdown)

# Create new post
blogdown::new_post(
  title = "Your Post Title",
  author = "Nate Fristoe",
  ext = ".md",
  categories = c("category1", "category2"),
  tags = c("tag1", "tag2")
)
```

### Manual Creation
1. Create new file in `content/post/` with format: `YYYY-MM-DD-post-title.md`
2. Add front matter:
```yaml
---
title: "Your Post Title"
author: "Nate Fristoe"
date: "2025-10-21"
slug: "your-post-slug"
categories:
  - category1
tags:
  - tag1
description: "Brief description for SEO"
featured_image: "/images/your-image.png"
---

Your content here...
```

3. Add images to `static/images/`
4. Commit and push

---

## Workflow Example

### Scenario: You have 5 active posts, want to add a 6th

**Current State**:
- Homepage shows 3 most recent posts
- You have 5 posts total in `content/post/`
- Want to add a new post

**Steps**:
1. **Create new post** (will be the newest)
2. **Decide if archiving is needed**:
   - If you want only the 5 newest posts visible in the Posts section, archive the oldest
   - Homepage will still only show 3 most recent regardless
3. **Archive oldest post** (optional):
   ```bash
   git mv content/post/oldest-post.md content/post-archive/oldest-post.md
   ```
4. **Commit and push**:
   ```bash
   git add -A
   git commit -m "Add new post and archive old content"
   git push
   ```

---

## Understanding What Appears Where

### Homepage (`/`)
- Shows 3 most recent posts from `content/post/`
- Configured by: `recent_posts_number = 3` in config.toml
- Updates automatically based on post dates

### Posts Page (`/post/`)
- Shows ALL posts from `content/post/`
- Sorted by date (newest first)
- Does NOT include archived posts

### Post Archive Page (`/post-archive/`)
- Shows posts from `content/post-archive/`
- Not linked from main navigation
- Accessible via direct URL only

---

## Changing Homepage Post Count

To show more or fewer posts on the homepage:

**Edit `config.toml`**:
```toml
[params]
  recent_posts_number = 5  # Change from 3 to 5 (or any number)
```

**Commit and push**:
```bash
git add config.toml
git commit -m "Update homepage to show 5 recent posts"
git push
```

---

## Best Practices

1. **Regular archiving**: Review posts quarterly, archive outdated content
2. **Consistent dating**: Always use current date for new posts
3. **Good descriptions**: Write clear descriptions for SEO
4. **Image optimization**: Keep images under 500 KB (see IMAGE_OPTIMIZATION_GUIDE.md)
5. **Categories/tags**: Use consistent categories and tags for organization
6. **Git commits**: Always commit and push after making changes

---

## Troubleshooting

### Post not showing on homepage
- Check the date (must be current or recent)
- Verify it's in `content/post/` not `content/post-archive/`
- Check that filename is correct format: `YYYY-MM-DD-title.md`
- Verify front matter is properly formatted (YAML syntax)

### Post shows on Posts page but not homepage
- Homepage only shows 3 most recent posts
- Your post might be older than the 3 newest posts
- Increase `recent_posts_number` in config.toml if desired

### Archived post still showing
- Make sure you moved it to `content/post-archive/`
- Not just renamed it
- Commit and push the change
- Wait for Netlify to rebuild

---

**Summary**:
- New posts automatically appear on homepage (3 most recent)
- Archive old posts by moving them to `content/post-archive/`
- No automatic archiving - you control what stays active
- Hugo handles the rest automatically!
