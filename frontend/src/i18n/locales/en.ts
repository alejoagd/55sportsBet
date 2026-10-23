import type { Dictionary } from './es';

const en: Dictionary = {
  lang: { label: 'Language' },

  common: {
    retry: 'Retry',
    timeTbd: 'Time TBC',
    dateTbd: 'Date TBC',
    matchesCount_one: '{{count}} match',
    matchesCount_other: '{{count}} matches',
  },

  nav: {
    home: 'Home',
    bets: 'Bets',
    evolution: 'Trends',
    leagues: 'Leagues',
    subscribe: 'Subscribe',
    subscribeTooltip: 'Subscribe to stay up to date with 55sports Stats',
    adminAccess: 'Admin access',
    notFound: 'Page not found',
    backToDashboard: 'Back to Dashboard',
  },

  tabs: {
    today: 'Today',
    matches: 'Matches',
    standings: 'Standings',
    bracket: 'Bracket',
    news: 'News',
    stats: 'Stats',
  },

  sidebar: {
    leagues: 'Leagues',
    expandMenu: 'Expand leagues menu',
    collapseMenu: 'Collapse leagues menu',
    expand: 'Expand',
    collapse: 'Collapse',
    loading: 'Loading leagues...',
  },

  standings: {
    team: 'Team',
    played: 'P',
    won: 'W',
    drawn: 'D',
    lost: 'L',
    gf: 'GF',
    ga: 'GA',
    gd: 'GD',
    pts: 'Pts',
    group: 'Group {{name}}',
    loading: 'Loading standings...',
    error: 'Could not load the standings table',
    empty: 'No matches have been played yet this season',
  },

  today: {
    title: "Today's matches",
    loading: "Loading today's matches...",
    error: "Could not load today's matches",
    empty: 'There are no matches scheduled for today in any league',
  },

  dashboard: {
    loading: 'Loading predictions...',
    errorTitle: 'Error loading data',
    unknownError: 'Unknown error',
    upcomingToday: 'Upcoming today',
    playedToday: 'Played today',
    noMatchesTodayLeague: 'No matches in this league today',
    upcoming: 'Upcoming Matches',
    recent: 'Recent Results',
    noMatches: 'No matches available',
  },

  matchList: {
    match: 'Match',
    prob1x2: '1X2 Probability',
    pred: 'Pred.',
    score: 'Score',
    goals: 'Goals',
    noPrediction: 'No prediction',
    noPredictionAvailable: 'No prediction available',
    prediction: 'Prediction',
    avgGoals: 'Avg. Goals',
    fullTime: 'FT',
  },

  live: {
    live: 'LIVE',
    halftime: 'Half time',
    penalties: 'Penalties',
    final: 'Final',
    ownGoal: 'Own goal',
    goal: 'Goal',
    yellowCard: 'Yellow card',
    redCard: 'Red card',
  },

  news: {
    loading: 'Loading news...',
    error: 'Could not load the news',
    empty: 'No recent news for {{league}}',
    title: '{{league}} News',
    source: 'Source: Marca · updated hourly',
    originalLanguage: 'News is shown in its original language (Spanish).',
    readMore: 'Read more →',
  },

  footer: {
    legal: '<b>18+.</b> Gamble responsibly: betting can be addictive. 55sports Stats is an information and analysis platform; it is not a betting site and does not accept bets. Predictions are statistical estimates and do not guarantee results.',
    privacy: 'Privacy Policy',
  },

  countries: { scotland: 'Scotland', england: 'England', wales: 'Wales', other: 'Other' },

  subscribe: {
    title: 'Subscribe to 55sports Stats',
    subtitle: 'Stay up to date with predictions, results and news',
    close: 'Close',
    successTitle: 'Subscription successful! We will keep you informed.',
    successBody: 'We will keep you up to date with the predictions, analysis and news from 55sports Stats.',
    ok: 'Got it!',
    firstName: 'First name',
    lastName: 'Last name',
    email: 'Email',
    phone: 'Phone',
    country: 'Country',
    city: 'City',
    firstNamePh: 'E.g. John',
    lastNamePh: 'E.g. Smith',
    cityPh: 'E.g. Bogotá',
    select: 'Select...',
    consent: 'I authorize 55sports Stats to process my personal data (name, email, phone, country and city) to send me information about predictions, results and platform news, in accordance with <b>Law 1581 of 2012</b> (Colombia) and the <privacy>Privacy Policy</privacy>. I can withdraw my authorization at any time. <req>*Required</req>',
    submit: 'Subscribe now!',
    submitting: 'Registering...',
    errRequired: 'Required field',
    errEmail: 'Invalid email',
    errPhone: 'Invalid phone number',
    errCountry: 'Select a country',
    errAccept: 'You must accept to continue',
    errDuplicate: 'This email is already registered.',
    errInvalid: 'Please check your details and try again.',
    errGeneric: 'Something went wrong. Please try again.',
    errNetwork: 'Could not connect. Check your connection.',
  },

  privacy: {
    title: 'Privacy Policy',
    back: '← Back to 55sports Stats',
    validSince: 'Effective since {{date}}',
    s1: {
      title: '1. Data controller',
      p1: '<b>{{owner}}</b>, owner of the 55sports Stats platform (hereinafter, "55sports Stats"), is the controller of the personal data described in this policy, in accordance with Colombian Law 1581 of 2012, Decree 1377 of 2013 and any rules that amend or supplement them.',
      p2: 'Contact for questions, claims and exercising your rights: <b>{{email}}</b>',
    },
    s2: {
      title: '2. What data we collect',
      p1: 'Only when you subscribe voluntarily: first name, last name, email, phone number, country and city. We do not collect sensitive data, and we do not ask for passwords, bank details or payment methods.',
      p2: 'We also use web analytics (Vercel Web Analytics), which records aggregated usage metrics for the site, such as pages visited and device type, to understand and improve the platform.',
    },
    s3: {
      title: '3. What we use your data for',
      i1: 'Managing your subscription to 55sports Stats.',
      i2: 'Sending you information about predictions, results, analysis and platform news.',
      i3: 'Answering your questions and requests.',
      i4: 'Improving the content and operation of the service.',
      p1: 'We do not sell or transfer your data to third parties for commercial purposes.',
    },
    s4: {
      title: '4. Authorization',
      p1: 'Processing is carried out with your prior, express and informed authorization, which you give by ticking the box on the subscription form. You can withdraw it at any time by writing to {{email}}.',
    },
    s5: {
      title: '5. Your rights',
      p1: 'As the data subject you have the right to:',
      i1: 'Know, update and correct your personal data.',
      i2: 'Request proof of the authorization you gave.',
      i3: 'Be informed about how your data has been used.',
      i4: 'Withdraw your authorization and/or request deletion of your data.',
      i5: 'File complaints with the Superintendence of Industry and Commerce (SIC) of Colombia.',
      i6: 'Access your personal data free of charge.',
      p2: 'To exercise them, write to {{email}} stating your name and subscription email. Queries are answered within 10 business days and claims within 15 business days, extendable under the terms of the law.',
    },
    s6: {
      title: '6. Where the data is stored',
      p1: 'The infrastructure of 55sports Stats (server, database and website) is hosted with cloud service providers located in the United States. This involves an international transfer of data, carried out with providers that apply appropriate security measures.',
    },
    s7: {
      title: '7. Security and retention',
      p1: 'We apply reasonable technical and administrative measures to protect your data against unauthorized access, loss or alteration. We keep it while your subscription is active or until you request its deletion.',
    },
    s8: {
      title: '8. Minors',
      p1: '55sports Stats is intended for people aged 18 or over. We do not knowingly collect data from minors; if we detect that a minor has registered, we will delete their data.',
    },
    s9: {
      title: '9. Informational nature and third-party trademarks',
      p1: '55sports Stats is an information and statistical analysis platform. It is not a betting site, it does not accept or manage bets or money, and its predictions are estimates that do not guarantee results.',
      p2: 'The names, crests and trademarks of teams and competitions belong to their respective owners. 55sports Stats is independent and is not affiliated with or endorsed by them.',
    },
    s10: {
      title: '10. Changes to this policy',
      p1: 'We may update this policy. The current version will always be published on this page, with its effective date.',
    },
  },
};

export default en;
