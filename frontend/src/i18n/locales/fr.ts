import type { Dictionary } from './es';

const fr: Dictionary = {
  lang: { label: 'Langue' },

  common: {
    retry: 'Réessayer',
    timeTbd: 'Heure à confirmer',
    dateTbd: 'Date à confirmer',
    matchesCount_one: '{{count}} match',
    matchesCount_other: '{{count}} matchs',
  },

  nav: {
    home: 'Accueil',
    bets: 'Paris',
    evolution: 'Évolution',
    leagues: 'Ligues',
    subscribe: "S'abonner",
    subscribeTooltip: "Abonnez-vous pour suivre l'actualité de 55sports Stats",
    adminAccess: 'Accès administrateur',
    notFound: 'Page introuvable',
    backToDashboard: 'Retour au tableau de bord',
  },

  tabs: {
    today: "Aujourd'hui",
    matches: 'Matchs',
    standings: 'Classement',
    bracket: 'Tableau',
    news: 'Actualités',
    stats: 'Statistiques',
  },

  sidebar: {
    leagues: 'Ligues',
    expandMenu: 'Développer le menu des ligues',
    collapseMenu: 'Réduire le menu des ligues',
    expand: 'Développer',
    collapse: 'Réduire',
    loading: 'Chargement des ligues...',
  },

  standings: {
    team: 'Équipe',
    played: 'J',
    won: 'G',
    drawn: 'N',
    lost: 'P',
    gf: 'BP',
    ga: 'BC',
    gd: 'DB',
    pts: 'Pts',
    group: 'Groupe {{name}}',
    loading: 'Chargement du classement...',
    error: 'Impossible de charger le classement',
    empty: "Aucun match n'a encore été joué cette saison",
  },

  today: {
    title: "Matchs d'aujourd'hui",
    loading: "Chargement des matchs d'aujourd'hui...",
    error: "Impossible de charger les matchs d'aujourd'hui",
    empty: "Aucun match n'est prévu aujourd'hui dans aucune ligue",
  },

  dashboard: {
    loading: 'Chargement des pronostics...',
    errorTitle: 'Erreur de chargement des données',
    unknownError: 'Erreur inconnue',
    upcomingToday: "À venir aujourd'hui",
    playedToday: "Joués aujourd'hui",
    noMatchesTodayLeague: "Aucun match de cette ligue aujourd'hui",
    upcoming: 'Prochains Matchs',
    recent: 'Résultats Récents',
    noMatches: 'Aucun match disponible',
  },

  matchList: {
    match: 'Match',
    prob1x2: 'Probabilité 1X2',
    pred: 'Pron.',
    score: 'Score',
    goals: 'Buts',
    noPrediction: 'Pas de pronostic',
    noPredictionAvailable: 'Aucun pronostic disponible',
    prediction: 'Pronostic',
    avgGoals: 'Moy. de buts',
    fullTime: 'FT',
  },

  live: {
    live: 'EN DIRECT',
    halftime: 'Mi-temps',
    penalties: 'Tirs au but',
    final: 'Terminé',
    ownGoal: 'But contre son camp',
    goal: 'But',
    yellowCard: 'Carton jaune',
    redCard: 'Carton rouge',
  },

  news: {
    loading: 'Chargement des actualités...',
    error: 'Impossible de charger les actualités',
    empty: 'Aucune actualité récente pour {{league}}',
    title: 'Actualités {{league}}',
    source: 'Source : Marca · mis à jour toutes les heures',
    originalLanguage: "Les actualités sont affichées dans leur langue d'origine (espagnol).",
    readMore: 'Lire la suite →',
  },

  footer: {
    legal: "<b>18+.</b> Jouez de manière responsable : les paris peuvent créer une dépendance. 55sports Stats est une plateforme d'information et d'analyse ; ce n'est pas un site de paris et il n'accepte aucun pari. Les pronostics sont des estimations statistiques et ne garantissent aucun résultat.",
    privacy: 'Politique de confidentialité',
  },

  countries: { scotland: 'Écosse', england: 'Angleterre', wales: 'Pays de Galles', other: 'Autre' },

  subscribe: {
    title: 'Abonnez-vous à 55sports Stats',
    subtitle: "Suivez l'actualité : pronostics, résultats et nouveautés",
    close: 'Fermer',
    successTitle: 'Abonnement réussi ! Nous vous tiendrons informé.',
    successBody: "Nous vous tiendrons informé des pronostics, analyses et nouveautés de 55sports Stats.",
    ok: 'Compris !',
    firstName: 'Prénom',
    lastName: 'Nom',
    email: 'E-mail',
    phone: 'Téléphone',
    country: 'Pays',
    city: 'Ville',
    firstNamePh: 'Ex. : Jean',
    lastNamePh: 'Ex. : Dupont',
    cityPh: 'Ex. : Bogotá',
    select: 'Sélectionner...',
    consent: "J'autorise 55sports Stats à traiter mes données personnelles (nom, e-mail, téléphone, pays et ville) afin de m'envoyer des informations sur les pronostics, les résultats et les nouveautés de la plateforme, conformément à la <b>Loi 1581 de 2012</b> (Colombie) et à la <privacy>Politique de confidentialité</privacy>. Je peux retirer mon autorisation à tout moment. <req>*Obligatoire</req>",
    submit: "Je m'abonne maintenant !",
    submitting: 'Enregistrement...',
    errRequired: 'Champ obligatoire',
    errEmail: 'E-mail invalide',
    errPhone: 'Téléphone invalide',
    errCountry: 'Sélectionnez un pays',
    errAccept: 'Vous devez accepter pour continuer',
    errDuplicate: 'Cet e-mail est déjà enregistré.',
    errInvalid: 'Vérifiez vos informations et réessayez.',
    errGeneric: 'Une erreur est survenue. Réessayez.',
    errNetwork: 'Connexion impossible. Vérifiez votre connexion.',
  },

  privacy: {
    title: 'Politique de confidentialité',
    back: '← Retour à 55sports Stats',
    validSince: 'En vigueur depuis le {{date}}',
    s1: {
      title: '1. Responsable du traitement',
      p1: "<b>{{owner}}</b>, titulaire de la plateforme 55sports Stats (ci-après, « 55sports Stats »), est le responsable du traitement des données personnelles décrites dans la présente politique, conformément à la loi colombienne 1581 de 2012, au décret 1377 de 2013 et aux autres textes qui les modifient ou les complètent.",
      p2: "Contact pour les questions, réclamations et l'exercice de vos droits : <b>{{email}}</b>",
    },
    s2: {
      title: '2. Quelles données nous collectons',
      p1: "Uniquement lorsque vous vous abonnez volontairement : prénom, nom, e-mail, téléphone, pays et ville. Nous ne collectons pas de données sensibles et ne demandons ni mots de passe, ni coordonnées bancaires, ni moyens de paiement.",
      p2: "Nous utilisons également des statistiques web (Vercel Web Analytics), qui enregistrent des mesures d'utilisation agrégées du site, comme les pages visitées et le type d'appareil, afin de comprendre et d'améliorer la plateforme.",
    },
    s3: {
      title: '3. À quoi servent vos données',
      i1: 'Gérer votre abonnement à 55sports Stats.',
      i2: 'Vous envoyer des informations sur les pronostics, les résultats, les analyses et les nouveautés de la plateforme.',
      i3: 'Répondre à vos questions et à vos demandes.',
      i4: 'Améliorer le contenu et le fonctionnement du service.',
      p1: 'Nous ne vendons ni ne cédons vos données à des tiers à des fins commerciales.',
    },
    s4: {
      title: '4. Autorisation',
      p1: "Le traitement est effectué avec votre autorisation préalable, expresse et éclairée, que vous donnez en cochant la case du formulaire d'abonnement. Vous pouvez la retirer à tout moment en écrivant à {{email}}.",
    },
    s5: {
      title: '5. Vos droits',
      p1: 'En tant que titulaire des données, vous avez le droit de :',
      i1: 'Connaître, mettre à jour et rectifier vos données personnelles.',
      i2: "Demander la preuve de l'autorisation accordée.",
      i3: "Être informé de l'usage qui a été fait de vos données.",
      i4: "Retirer l'autorisation et/ou demander la suppression de vos données.",
      i5: "Déposer une plainte auprès de la Surintendance de l'Industrie et du Commerce (SIC) de Colombie.",
      i6: 'Accéder gratuitement à vos données personnelles.',
      p2: "Pour les exercer, écrivez à {{email}} en indiquant votre nom et l'e-mail utilisé pour l'abonnement. Les demandes sont traitées sous 10 jours ouvrables et les réclamations sous 15 jours ouvrables, prorogeables dans les conditions prévues par la loi.",
    },
    s6: {
      title: '6. Où les données sont stockées',
      p1: "L'infrastructure de 55sports Stats (serveur, base de données et site web) est hébergée chez des prestataires de services cloud situés aux États-Unis. Cela implique un transfert international de données, réalisé avec des prestataires qui appliquent des mesures de sécurité adéquates.",
    },
    s7: {
      title: '7. Sécurité et conservation',
      p1: "Nous appliquons des mesures techniques et administratives raisonnables pour protéger vos données contre tout accès non autorisé, perte ou altération. Nous les conservons tant que votre abonnement est actif ou jusqu'à ce que vous en demandiez la suppression.",
    },
    s8: {
      title: '8. Mineurs',
      p1: "55sports Stats s'adresse aux personnes de plus de 18 ans. Nous ne collectons pas sciemment de données de mineurs ; si nous constatons qu'un mineur s'est inscrit, nous supprimerons ses données.",
    },
    s9: {
      title: '9. Nature informative et marques de tiers',
      p1: "55sports Stats est une plateforme d'information et d'analyse statistique. Ce n'est pas un site de paris, il ne reçoit ni ne gère de paris ni d'argent, et ses pronostics sont des estimations qui ne garantissent aucun résultat.",
      p2: "Les noms, écussons et marques des équipes et des compétitions appartiennent à leurs propriétaires respectifs. 55sports Stats est indépendante et n'est ni affiliée à eux ni approuvée par eux.",
    },
    s10: {
      title: '10. Modifications de cette politique',
      p1: "Nous pouvons mettre à jour cette politique. La version en vigueur sera toujours publiée sur cette page, avec sa date d'entrée en vigueur.",
    },
  },
};

export default fr;
