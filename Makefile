# NixVir Website - Common Commands
# Usage: make <command>

.PHONY: help preview build deploy news snow dashboard snotel status new-post

help: ## Show available commands
	@echo.
	@echo   NixVir Website Commands
	@echo   =======================
	@echo.
	@echo   Content:
	@echo     make preview        Start local preview server (http://localhost:1313)
	@echo     make preview-drafts Preview including draft posts
	@echo     make new-post       Create a new blog post (prompts for title)
	@echo     make build          Build site for production
	@echo.
	@echo   Data Pipelines (run locally):
	@echo     make news           Update ski industry news feed
	@echo     make snow           Update snow cover data
	@echo     make dashboard      Update economic dashboard data
	@echo     make snotel         Update SNOTEL snowpack data
	@echo.
	@echo   Deployment:
	@echo     make deploy         Build, commit, and push to deploy
	@echo     make status         Check data feed health
	@echo.

# === Content ===

preview: ## Start Hugo dev server
	hugo server --navigateToChanged

preview-drafts: ## Start Hugo dev server with drafts
	hugo server -D --navigateToChanged

new-post: ## Create a new blog post
	@set /p TITLE="Post title: " && \
	hugo new post/%DATE:~0,4%-%DATE:~5,2%-%DATE:~8,2%-$$TITLE.md && \
	echo Post created. Edit in content/post/

build: ## Build site for production
	hugo --minify

# === Data Pipelines ===

news: ## Update ski industry news
	python update_ski_news.py

snow: ## Update snow cover data
	python update_snow_cover.py

dashboard: ## Update economic dashboard
	python update_dashboard.py

snotel: ## Update SNOTEL snowpack
	python fetch_snotel_data.py

# === Deployment ===

deploy: build ## Build and deploy
	@echo Deploying to Netlify via git push...
	git add -A
	git status
	@echo.
	@echo Review staged changes above. Press Ctrl+C to cancel.
	@pause
	git commit -m "Update site content"
	git push

status: ## Open data feed status page
	start https://www.nixvir.com/data-status
