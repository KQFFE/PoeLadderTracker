const { test, expect } = require('@playwright/test');

function makeEntries(count, leagueName = 'Affliction') {
  return Array.from({ length: count }, (_, index) => ({
    rank: index + 1,
    character: {
      name: index === 0 ? 'AlphaRunner' : `Runner${index + 1}`,
      class: index % 2 === 0 ? 'Champion' : 'Elementalist',
      level: 90 + (index % 10),
      experience: 1000000 + index * 5000,
    },
    account: {
      name: `Account${index + 1}`,
    },
  }));
}

test.describe('PoeLadderTracker', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/leagues', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { id: 'Affliction', text: 'Affliction' },
          { id: 'Standard', text: 'Standard' },
        ]),
      });
    });

    await page.route('**/public-ladder/**', async (route) => {
      const url = new URL(route.request().url());
      const offset = Number(url.searchParams.get('offset') || 0);
      const limit = Number(url.searchParams.get('limit') || 10);
      const league = decodeURIComponent(url.pathname.split('/').filter(Boolean).slice(-1)[0] || 'Affliction');

      const entries = makeEntries(limit, league).map((entry, index) => ({
        ...entry,
        rank: offset + index + 1,
        character: {
          ...entry.character,
          name: offset === 0 && index === 0 ? 'AlphaRunner' : `Runner${offset + index + 1}`,
        },
      }));

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ entries }),
      });
    });

    await page.goto('/');
  });

  test('loads the main app and renders the expected controls', async ({ page }) => {
    await expect(page).toHaveTitle(/PoE Ladder Tracker/i);
    await expect(page.locator('#leagueSelect')).toBeVisible();
    await expect(page.locator('#ascendancySelect')).toBeVisible();
    await expect(page.locator('#fetchBtn')).toBeVisible();
    await expect(page.locator('#charNameInput')).toBeVisible();
    await expect(page.locator('#searchBtn')).toBeVisible();
    await expect(page.locator('#raceBtn')).toBeDisabled();

    const options = await page.locator('#leagueSelect option').allTextContents();
    expect(options).toContain('Affliction');
  });

  test('fetches ladder data and shows results for a selected league', async ({ page }) => {
    await page.selectOption('#leagueSelect', 'Affliction');
    await page.selectOption('#ascendancySelect', 'Champion');
    await page.click('#fetchBtn');

    await expect(page.locator('#resultsBox')).toContainText('Runner1');
    await expect(page.locator('#status')).toContainText('Done');
    await expect(page.locator('#showMoreBtn')).toBeEnabled();
  });

  test('search finds a specific character and enables race mode', async ({ page }) => {
    await page.selectOption('#leagueSelect', 'Affliction');
    await page.fill('#charNameInput', 'AlphaRunner');
    await page.click('#searchBtn');

    await expect(page.locator('#resultsBox')).toContainText('Character Found');
    await expect(page.locator('#resultsBox')).toContainText('AlphaRunner');
    await expect(page.locator('#raceBtn')).toBeEnabled();
  });
});
