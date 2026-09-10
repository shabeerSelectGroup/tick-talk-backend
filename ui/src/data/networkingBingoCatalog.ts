/** Mirror of backend bingo catalog — used when API list is empty but event is networking. */

export type BingoCatalogItem = {
  slug: string
  category: string
  title: string
  description: string
}

export const NETWORKING_BINGO_CATALOG: BingoCatalogItem[] = [
  { slug: 'bingo-loves-traveling', category: 'travel', title: 'Loves traveling', description: 'Find someone who loves traveling' },
  { slug: 'bingo-visited-5-countries', category: 'travel', title: 'Has visited more than 5 countries', description: 'Find someone who has visited more than 5 countries' },
  { slug: 'bingo-enjoys-road-trips', category: 'travel', title: 'Enjoys road trips', description: 'Find someone who enjoys road trips' },
  { slug: 'bingo-lived-another-city', category: 'travel', title: 'Has lived in another city', description: 'Find someone who has lived in another city' },
  { slug: 'bingo-loves-adventure', category: 'travel', title: 'Loves adventure activities', description: 'Find someone who loves adventure activities' },
  { slug: 'bingo-works-in-hr', category: 'professional', title: 'Works in HR', description: 'Find someone who works in HR' },
  { slug: 'bingo-works-in-finance', category: 'professional', title: 'Works in Finance', description: 'Find someone who works in Finance' },
  { slug: 'bingo-works-in-it', category: 'professional', title: 'Works in IT', description: 'Find someone who works in IT' },
  { slug: 'bingo-manages-team', category: 'professional', title: 'Manages a team', description: 'Find someone who manages a team' },
  { slug: 'bingo-experience-10-years', category: 'professional', title: 'Has more than 10 years of experience', description: 'Find someone with more than 10 years of experience' },
  { slug: 'bingo-good-with-technology', category: 'skills', title: 'Good with technology', description: 'Find someone who is good with technology' },
  { slug: 'bingo-speaks-3-languages', category: 'skills', title: 'Speaks 3 or more languages', description: 'Find someone who speaks 3 or more languages' },
  { slug: 'bingo-public-speaking', category: 'skills', title: 'Good at public speaking', description: 'Find someone who is good at public speaking' },
  { slug: 'bingo-problem-solver', category: 'skills', title: 'Excellent problem solver', description: 'Find someone who is an excellent problem solver' },
  { slug: 'bingo-professional-cert', category: 'skills', title: 'Has completed a professional certification', description: 'Find someone who has completed a professional certification' },
  { slug: 'bingo-plays-sports', category: 'fun_facts', title: 'Plays sports regularly', description: 'Find someone who plays sports regularly' },
  { slug: 'bingo-loves-football', category: 'fun_facts', title: 'Loves football', description: 'Find someone who loves football' },
  { slug: 'bingo-loves-cricket', category: 'fun_facts', title: 'Loves cricket', description: 'Find someone who loves cricket' },
  { slug: 'bingo-enjoys-cooking', category: 'fun_facts', title: 'Enjoys cooking', description: 'Find someone who enjoys cooking' },
  { slug: 'bingo-loves-movies', category: 'fun_facts', title: 'Loves watching movies', description: 'Find someone who loves watching movies' },
  { slug: 'bingo-intl-conference', category: 'networking', title: 'Has attended an international conference', description: 'Find someone who has attended an international conference' },
  { slug: 'bingo-trained-team', category: 'networking', title: 'Has trained a team', description: 'Find someone who has trained a team' },
  { slug: 'bingo-led-project', category: 'networking', title: 'Has led a project', description: 'Find someone who has led a project' },
  { slug: 'bingo-mentors-others', category: 'networking', title: 'Mentors others', description: 'Find someone who mentors others' },
  { slug: 'bingo-multiple-industries', category: 'networking', title: 'Has worked in multiple industries', description: 'Find someone who has worked in multiple industries' },
  { slug: 'bingo-birthday-this-month', category: 'ice_breakers', title: 'Is celebrating a birthday this month', description: 'Find someone celebrating a birthday this month' },
  { slug: 'bingo-unique-hobby', category: 'ice_breakers', title: 'Has a unique hobby', description: 'Find someone with a unique hobby' },
  { slug: 'bingo-coffee-daily', category: 'ice_breakers', title: 'Drinks coffee every day', description: 'Find someone who drinks coffee every day' },
  { slug: 'bingo-prefers-tea', category: 'ice_breakers', title: 'Prefers tea over coffee', description: 'Find someone who prefers tea over coffee' },
  { slug: 'bingo-new-role-year', category: 'ice_breakers', title: 'Started a new role within the last year', description: 'Find someone who started a new role within the last year' },
]
