// Assina o APK de release com a chave do projeto.
// A senha e o caminho da chave NUNCA ficam no repositório: vêm de
// ~/.gradle/gradle.properties (DUOCASH_STORE_FILE, DUOCASH_STORE_PASSWORD,
// DUOCASH_KEY_ALIAS, DUOCASH_KEY_PASSWORD).
// Segurança: um build de release SEM a chave falha, em vez de cair na chave
// pública de debug (que permitiria a qualquer um gerar uma "atualização" falsa).
const { withAppBuildGradle } = require("expo/config-plugins");

const SIGNING = `
        release {
            if (project.hasProperty('DUOCASH_STORE_FILE')) {
                storeFile file(DUOCASH_STORE_FILE)
                storePassword DUOCASH_STORE_PASSWORD
                keyAlias DUOCASH_KEY_ALIAS
                keyPassword DUOCASH_KEY_PASSWORD
            }
        }`;

const GUARD = `
gradle.taskGraph.whenReady { graph ->
    def releaseTask = graph.allTasks.any { it.name.toLowerCase().contains("release") }
    if (releaseTask && !project.hasProperty('DUOCASH_STORE_FILE')) {
        throw new GradleException("DuoCash: chave de assinatura não configurada (DUOCASH_STORE_FILE em ~/.gradle/gradle.properties). Veja docs/deploy.md.")
    }
}
`;

module.exports = function withReleaseSigning(config) {
  return withAppBuildGradle(config, (cfg) => {
    let src = cfg.modResults.contents;
    if (!src.includes("DUOCASH_STORE_FILE")) {
      src = src.replace(/signingConfigs\s*\{/, (m) => `${m}${SIGNING}`);
      src = src.replace(
        /(buildTypes\s*\{[\s\S]*?release\s*\{[\s\S]*?)signingConfig signingConfigs\.debug/,
        "$1signingConfig signingConfigs.release",
      );
      src += GUARD;
    }
    cfg.modResults.contents = src;
    return cfg;
  });
};
