document.getElementById("year").textContent = new Date().getFullYear();

(() => {
  const username = "FaramarzKowsari";
  const rootRepo = `${username}.github.io`;
  const grid = document.getElementById("repo-grid");
  const status = document.getElementById("repo-status");
  const count = document.getElementById("repo-count");
  const search = document.getElementById("repo-search");
  const sort = document.getElementById("repo-sort");
  let repositories = [];

  const escapeHtml = (value = "") => String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

  const prettyName = (name) => name
    .replaceAll("-", " ")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());

  const projectUrl = (repo) => {
    if (repo.homepage && /^https?:\/\//i.test(repo.homepage)) return repo.homepage;
    if (repo.has_pages && repo.name !== rootRepo) {
      return `https://${username.toLowerCase()}.github.io/${repo.name}/`;
    }
    return "";
  };

  const normalizeRepo = (repo) => ({
    name: repo.name || "",
    description: repo.description || "",
    language: repo.language || "",
    topics: Array.isArray(repo.topics) ? repo.topics : [],
    archived: Boolean(repo.archived),
    fork: Boolean(repo.fork),
    has_pages: Boolean(repo.has_pages),
    homepage: repo.homepage || "",
    html_url: repo.html_url || `https://github.com/${username}/${repo.name}`,
    stargazers_count: Number(repo.stargazers_count || 0),
    pushed_at: repo.pushed_at || repo.updated_at || "1970-01-01T00:00:00Z"
  });

  const render = () => {
    const q = search.value.trim().toLowerCase();
    let items = repositories.filter((repo) => {
      const haystack = [
        repo.name,
        repo.description,
        repo.language,
        ...(repo.topics || [])
      ].join(" ").toLowerCase();
      return !q || haystack.includes(q);
    });

    if (sort.value === "name") {
      items.sort((a, b) => a.name.localeCompare(b.name));
    } else if (sort.value === "stars") {
      items.sort((a, b) =>
        b.stargazers_count - a.stargazers_count ||
        new Date(b.pushed_at) - new Date(a.pushed_at)
      );
    } else {
      items.sort((a, b) => new Date(b.pushed_at) - new Date(a.pushed_at));
    }

    count.textContent = `${items.length} of ${repositories.length} repositories`;

    if (!items.length) {
      grid.innerHTML = "";
      status.hidden = false;
      status.textContent = q
        ? "No repositories match this search."
        : "No public repositories were found.";
      return;
    }

    status.hidden = true;
    grid.innerHTML = items.map((repo) => {
      const live = projectUrl(repo);
      const topics = (repo.topics || [])
        .slice(0, 5)
        .map((topic) => `<span class="tag">${escapeHtml(topic)}</span>`)
        .join("");

      const metaParts = [
        repo.language || null,
        repo.archived ? "Archived" : null,
        `★ ${repo.stargazers_count}`
      ].filter(Boolean);

      const meta = metaParts
        .map((item) => `<span>${escapeHtml(item)}</span>`)
        .join("");

      return `
        <article class="project-card repo-card">
          <div class="repo-meta">${meta}</div>
          <h3>${escapeHtml(prettyName(repo.name))}</h3>
          <p>${escapeHtml(repo.description || "Public GitHub repository by Faramarz Kowsari.")}</p>
          ${topics ? `<div class="tags">${topics}</div>` : ""}
          <div class="project-links">
            ${live ? `<a href="${escapeHtml(live)}">Live site →</a>` : ""}
            <a href="${escapeHtml(repo.html_url)}">Repository</a>
          </div>
        </article>`;
    }).join("");
  };

  const fetchGeneratedIndex = async () => {
    const response = await fetch(`projects.json?v=${Date.now()}`, { cache: "no-store" });
    if (!response.ok) throw new Error("Local project index is not available");
    const data = await response.json();
    if (!Array.isArray(data)) throw new Error("Invalid project index");
    return data.map(normalizeRepo);
  };

  const fetchGitHub = async () => {
    const all = [];
    let page = 1;

    while (page <= 50) {
      const response = await fetch(
        `https://api.github.com/users/${username}/repos?type=owner&sort=updated&direction=desc&per_page=100&page=${page}`,
        { headers: { Accept: "application/vnd.github+json" } }
      );

      if (!response.ok) {
        throw new Error(`GitHub API returned ${response.status}`);
      }

      const batch = await response.json();
      all.push(...batch.map(normalizeRepo));

      if (batch.length < 100) break;
      page += 1;
    }

    return all;
  };

  const loadRepositories = async () => {
    try {
      let data;
      try {
        data = await fetchGeneratedIndex();
      } catch {
        data = await fetchGitHub();
      }

      repositories = data.filter(
        (repo) => !repo.fork && repo.name !== rootRepo
      );

      render();
    } catch (error) {
      console.error(error);
      status.hidden = false;
      status.innerHTML =
        `The live repository catalogue could not be loaded right now. ` +
        `<a href="https://github.com/${username}?tab=repositories">Open the full GitHub repository list →</a>`;
      count.textContent = "GitHub catalogue unavailable";
    }
  };

  search.addEventListener("input", render);
  sort.addEventListener("change", render);
  loadRepositories();
})();
