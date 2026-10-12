export const metadata = { title: "Données et limites | MedAI Lab" };

export default function Limites() {
  return (
    <article className="max-w-[68ch] space-y-10">
      <header>
        <h1 className="text-3xl font-semibold tracking-tight">Données et limites</h1>
        <p className="mt-4">
          Ce projet est un prototype de recherche. Il ne remplace pas l&apos;avis d&apos;un professionnel de santé et ne
          doit servir à aucune décision clinique.
        </p>
      </header>

      <section>
        <h2 className="text-xl font-semibold">Jeu de données</h2>
        <p className="mt-2">
          PneumoniaMNIST (MedMNIST v2), radiographies thoraciques pédiatriques annotées « pneumonie » ou « normal »,
          licence CC BY 4.0. Source d&apos;origine : Kermany et al., Cell, 2018. Redistribution : Yang et al., Scientific
          Data, 2023. Aucune donnée personnelle de santé n&apos;est utilisée.
        </p>
        <p className="mt-2">
          Effectifs lus par le pipeline (fiche de données <code>reports/datasheets/pneumoniamnist_224.json</code>) :
          entraînement 4 708 images (3 494 pneumonies), validation 524 (389), test 624 (390).
        </p>
      </section>

      <section>
        <h2 className="text-xl font-semibold">Ce que ces données ne permettent pas de conclure</h2>
        <ul className="mt-2 list-disc space-y-2 pl-5">
          <li>
            Population pédiatrique d&apos;un seul centre. Rien ne montre que les modèles fonctionnent sur des adultes ou
            avec d&apos;autres appareils.
          </li>
          <li>
            La prévalence de pneumonie vaut environ 74 % en entraînement et en validation, mais 62,5 % en test. Les
            seuils choisis sur la validation sont donc appliqués à une population un peu différente.
          </li>
          <li>
            Entre l&apos;entraînement et la validation, 10 paires d&apos;images sont des doublons confirmés (corrélation des
            pixels d&apos;au moins 0,99), dont 8 identiques au pixel près. La validation n&apos;est pas totalement
            indépendante de l&apos;entraînement : le choix de l&apos;epoch et des seuils peut en être légèrement
            optimiste. Aucun doublon confirmé n&apos;existe entre l&apos;entraînement et le test.
          </li>
          <li>
            MedMNIST réduit la résolution des images. La séparation par patient entre les jeux n&apos;est pas vérifiable
            avec les métadonnées disponibles.
          </li>
        </ul>
      </section>

      <section>
        <h2 className="text-xl font-semibold">Explicabilité</h2>
        <p className="mt-2">
          Les cartes Grad-CAM indiquent où le modèle a puisé de l&apos;information, pas pourquoi il décide. Tant que le test
          de sanité par randomisation des poids n&apos;est pas passé pour un modèle, l&apos;interface le signale. Aucun
          radiologue n&apos;a relu ces cartes.
        </p>
      </section>

      <section>
        <h2 className="text-xl font-semibold">Protocole</h2>
        <p className="mt-2">
          Le protocole est publié et versionné dans le dépôt (<code>docs/EVAL_PROTOCOL.md</code>). Le jeu de test sert une
          seule fois par seed, l&apos;epoch et les seuils sont choisis sur la validation, et tous les résultats sont publiés,
          y compris les moins bons.
        </p>
      </section>
    </article>
  );
}
