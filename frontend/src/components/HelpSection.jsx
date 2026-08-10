import { useState } from 'react'
import PropTypes from 'prop-types'

export default function HelpSection() {
  const [open, setOpen] = useState(false)
  const contentId = 'help-section-content'

  return (
    <div className="help-shell">
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
        aria-controls={contentId}
        className="help-toggle"
      >
        <span>Como usar</span>
        <span className="t-soft">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div id={contentId} className="help-body space-y-4">
          <Section title="1. Acesso">
            Informe o usuário e senha fornecidos pelo administrador e clique em <strong>Entrar</strong>.
          </Section>

          <Section title="2. Escolher o modelo de cálculo">
            <ul className="list-disc list-inside space-y-1">
              <li>
                <strong>Modelo atual (oficial)</strong> — o cálculo por torneio que a federação usa
                hoje. É o padrão, e é o que gera a lista oficial.
              </li>
              <li>
                <strong>Modelo FIDE (por partida)</strong> — o cálculo por partida, com as
                adaptações do Art. 68. Exige as colunas <code>TimeControl</code> (STD, RPD ou BLZ) e{' '}
                <code>EndDate</code> preenchidas no arquivo de torneios, e a{' '}
                <strong>data de nascimento</strong> preenchida no arquivo de jogadores.
              </li>
              <li>
                <strong>Comparar os dois</strong> — roda os dois modelos sobre o mesmo envio e gera
                o comparativo. Aceita apenas o arquivo de jogadores de 12 colunas e torneios de
                Clássico.
              </li>
            </ul>
            <p className="mt-2">
              No modelo atual, o intervalo processa um torneio de cada vez, em cadeia. Nos demais, o
              intervalo selecionado é o <strong>período de cálculo</strong>: todas as partidas usam
              o rating do início do período e o arredondamento acontece uma única vez, no fim. Rodar
              cinco torneios de uma vez e rodar cinco vezes um torneio dão resultados diferentes —
              os dois estão certos, são períodos diferentes.
            </p>
          </Section>

          <Section title="3. Preparar os arquivos">
            <p className="mb-2">Você precisará dos seguintes arquivos:</p>
            <ul className="list-disc list-inside space-y-1">
              <li><strong>Lista de jogadores</strong> (<code>players.csv</code>) — lista de rating atual</li>
              <li><strong>Arquivo de torneios</strong> (<code>tournaments.csv</code>) — cabeçalho: <code>Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj</code>, mais <code>;TimeControl</code> no modelo FIDE e no comparativo</li>
              <li><strong>Arquivos binários</strong> — um por torneio, no formato <code>&lt;Ord&gt;-&lt;CrId&gt;.&lt;Tipo&gt;</code> (ex: <code>1-99999.TURX</code>)</li>
            </ul>
          </Section>

          <Section title="4. Carregar os arquivos">
            <p className="mb-2">Selecione cada arquivo no campo correspondente.</p>
            <p className="alert-warning-block">
              ⚠️ <strong>Atenção:</strong> Informe o <strong>número do primeiro torneio</strong> a processar e a <strong>quantidade de torneios</strong>.
              Esses dois campos determinam quais torneios serão processados. Valores incorretos resultarão em processamento errado ou ausência de resultados.
            </p>
          </Section>

          <Section title="5. Validação">
            O sistema valida automaticamente os arquivos ao carregá-los. Se houver erros, eles serão listados na tela — corrija os arquivos e carregue novamente.
          </Section>

          <Section title="6. Executar o ciclo">
            Se a validação for bem-sucedida, clique em <strong>Executar</strong>. Será exibido um resumo dos torneios processados;
            use <strong>Baixar ZIP</strong> na tela seguinte para obter a nova lista de rating e os arquivos de auditoria de cada torneio.
          </Section>

          <Section title="7. Sair">
            Clique em <strong>Sair</strong> para encerrar a sessão.
          </Section>
        </div>
      )}
    </div>
  )
}

function Section({ title, children }) {
  return (
    <div>
      <p className="section-title">{title}</p>
      <div>{children}</div>
    </div>
  )
}

Section.propTypes = {
  title: PropTypes.string.isRequired,
  children: PropTypes.node.isRequired,
}

