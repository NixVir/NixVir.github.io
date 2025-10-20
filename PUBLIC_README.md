# NixVir Website

Official website for NixVir - Market Research and Data Analysis Services

## About

NixVir provides research tools and data analysis services specializing in outdoor recreation and market research. We offer pragmatic, cost-effective solutions with an emphasis on efficiency and actionable insights.

**Live Site**: https://confident-jang-4183f9.netlify.app/

## Technology Stack

- **Static Site Generator**: [Hugo](https://gohugo.io/) v0.128.0
- **Theme**: [Ananke](https://github.com/theNewDynamic/gohugo-theme-ananke)
- **Content Management**: R + [blogdown](https://bookdown.org/yihui/blogdown/)
- **Hosting**: [Netlify](https://www.netlify.com/)
- **Version Control**: Git + GitHub
- **Analytics**: Google Analytics 4 (GA4)

## Features

- 📊 **Economic Dashboard** - Real-time economic indicators and market data
- 📝 **Blog Posts** - Industry insights and market research trends
- 📧 **Contact Form** - Integrated with Formspree
- 📱 **Responsive Design** - Mobile-friendly layout
- 🔍 **SEO Optimized** - Proper meta tags and descriptions

## Site Structure

```
nixvirweb/
├── content/              # All site content
│   ├── _index.md        # Homepage
│   ├── about/           # About page
│   ├── post/            # Active blog posts
│   ├── post-archive/    # Archived posts
│   ├── contact.md       # Contact page
│   └── dashboard.md     # Economic dashboard
├── static/              # Static assets
│   ├── images/          # Images
│   └── data/            # Dashboard data (JSON)
├── themes/              # Hugo theme files
├── config.toml          # Site configuration
└── netlify.toml         # Netlify deployment config
```

## Development

### Prerequisites

- R (>= 4.0)
- RStudio
- Hugo v0.128.0

### Local Development

1. Clone the repository:
   ```bash
   git clone https://github.com/NixVir/NixVir.github.io.git
   cd NixVir.github.io
   ```

2. Open in RStudio:
   ```r
   # Open nixvirweb.Rproj
   library(blogdown)
   serve_site()
   ```

3. View at http://localhost:4321

### Creating Content

**New Blog Post:**
```r
blogdown::new_post(
  title = "Your Post Title",
  author = "Nate Fristoe",
  ext = ".md"
)
```

**Add Images:**
Place images in `static/images/` and reference as `/images/filename.jpg`

## Deployment

The site automatically deploys to Netlify when changes are pushed to the `master` branch.

### Manual Build

```r
blogdown::build_site()
```

## Configuration

Key settings in `config.toml`:
- Site title and description
- Google Analytics tracking ID
- Social media links
- Navigation menu items

## Contributing

This is a personal/business website. For issues or suggestions, please open an issue on GitHub.

## License

Copyright © 2019-2025 NixVir. All rights reserved.

## Contact

For market research inquiries, visit the [contact page](https://confident-jang-4183f9.netlify.app/contact/).

---

**Note**: NixVir roughly means "Snowman" in Latin.
