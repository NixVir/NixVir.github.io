# NixVir Website Maintenance Guide

## Overview
This guide documents how to maintain and update your NixVir website using R, blogdown, Hugo, GitHub, and Netlify.

**Last Updated**: December 2024  
**Hugo Version**: 0.128.0  
**Theme**: Ananke (latest)

## Quick Reference

### Your Setup
- **Local Directory**: D:/websites/nixvirweb
- **GitHub Repository**: https://github.com/NixVir/NixVir.github.io
- **Live Site**: https://confident-jang-4183f9.netlify.app/
- **Google Analytics**: G-E2QD5PNRWE

### Key Technologies
- **R + blogdown**: Creates content and manages the site
- **Hugo**: Static site generator that builds your site
- **GitHub**: Version control and backup
- **Netlify**: Hosting and automatic deployment

## Daily Workflow

### 1. Starting Work on Your Site

Open RStudio and load your project:
- File -> Open Project -> D:/websites/nixvirweb/nixvirweb.Rproj

Then in the R console:
library(blogdown)
serve_site()

Your site will open at http://localhost:4321

### 2. Creating New Blog Posts

blogdown::new_post(
  title = "Your Post Title",
  author = "Nate Fristoe",
  ext = ".md"  # or .Rmd if you need R code
)

This creates a file in content/post/ and opens it for editing.

### 3. Editing Existing Content

**Blog Posts**: Located in content/post/
**About Page**: content/about/_index.md
**Images**: Place in static/images/

### 4. Saving and Publishing Changes

After making changes:
system("git status")           # Check what changed
system("git add -A")           # Add all changes
system("git commit -m \"Your message\"")  # Commit
system("git push")             # Push to GitHub

## Common Tasks

### Adding a New Page
1. Create file: file.create("content/services.md")
2. Add front matter:
---
title: "Services"
description: "Our market research services"
featured_image: "/images/mtnsky.jpg"
menu:
  main:
    weight: 3
---

### Updating Site Configuration
Edit config.toml for:
- Site title
- Base URL
- Google Analytics
- Social media links

### Adding Images
1. Place in static/images/
2. Reference as: ![Alt text](/images/your-image.jpg)

## Troubleshooting

### Site Will Not Build
blogdown::check_site()
blogdown::build_site()

### Server Will Not Start
blogdown::stop_server()
# Restart R: Session -> Restart R
library(blogdown)
serve_site()

### Git Issues
# Set identity if needed:
system("git config --global user.email \"Nate@nixvir.com\"")
system("git config --global user.name \"Nate Fristoe\"")

## File Structure
D:/websites/nixvirweb/
├── config.toml          # Main configuration
├── content/             # All content
│   ├── about/          # About page
│   └── post/           # Blog posts
├── static/             # Static files
│   └── images/         # Images
├── themes/             # Theme (do not edit)
├── public/             # Generated site
└── netlify.toml        # Netlify config

## Blog Post Template
---
title: "Market Research Trends 2025"
author: "Nate Fristoe"
date: "2025-01-15"
slug: "market-research-trends-2025"
categories:
  - Research
tags:
  - trends
  - analysis
description: "Key trends shaping market research"
featured_image: "/images/your-image.jpg"
---

Your content here...

## Emergency Procedures

### Reverting Changes
system("git log --oneline -10")       # See commits
system("git reset --hard HEAD~1")     # Revert last (careful!)

### If Site is Down
1. Check https://app.netlify.com
2. Check GitHub repository
3. Rebuild locally to find errors

## Resources
- Blogdown Book: https://bookdown.org/yihui/blogdown/
- Hugo Docs: https://gohugo.io/documentation/
- Ananke Theme: https://github.com/theNewDynamic/gohugo-theme-ananke
- Markdown Guide: https://www.markdownguide.org/

## Setup on New Computer
1. Install R and RStudio
2. install.packages("blogdown")
3. git clone https://github.com/NixVir/NixVir.github.io.git
4. blogdown::install_hugo(version = "0.128.0")
5. blogdown::serve_site()

