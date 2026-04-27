"""CLI tool for running the data pipeline."""

import click
import sys
from pathlib import Path
from loguru import logger

from config.settings import get_settings

# Configure logging
logger.remove()
logger.add(sys.stderr, format="<level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>")

from src.data_pipeline.pipeline import DataPipeline
from src.prediction.role_predictor import RolePredictor

settings = get_settings()


@click.group()
def cli():
    """Job Market Intelligence Data Pipeline CLI."""
    pass


@cli.command()
@click.option(
    "--source",
    "-s",
    multiple=True,
    default=settings.default_sources,
    help="Data source (linkedin, kaggle)"
)
@click.option(
    "--keyword",
    "-k",
    multiple=True,
    default=settings.default_keywords,
    help="Job search keywords"
)
@click.option(
    "--limit",
    "-l",
    default=settings.default_limit_per_source,
    help="Max jobs per source"
)
@click.option(
    "--output",
    "-o",
    default=str(settings.default_jobs_output_path),
    help="Output file path"
)
def fetch(source, keyword, limit, output):
    """Fetch job data from specified sources."""
    click.echo(f"🚀 Fetching job data...")
    click.echo(f"   Sources: {', '.join(source)}")
    click.echo(f"   Keywords: {', '.join(keyword)}")
    click.echo(f"   Limit per source: {limit}\n")

    try:
        pipeline = DataPipeline()
        jobs = pipeline.run(
            sources=list(source),
            keywords=list(keyword),
            limit_per_source=limit
        )

        # Save results
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        if output.endswith('.csv'):
            pipeline.save_to_csv(output)
        else:
            pipeline.save_to_json(output)

        # Show statistics
        stats = pipeline.get_statistics()
        click.echo("✅ Pipeline completed!")
        click.echo(f"\n📊 Statistics:")
        click.echo(f"   Total jobs: {stats.get('total_jobs', 0)}")
        click.echo(f"   Locations: {stats.get('locations', 0)}")
        click.echo(f"   Companies: {stats.get('companies', 0)}")
        click.echo(f"   Unique skills: {stats.get('unique_skills', 0)}")
        
        if stats.get('salary_stats', {}).get('count', 0) > 0:
            salary = stats['salary_stats']
            click.echo(f"\n💰 Salary Statistics:")
            click.echo(f"   Average: ${salary['mean']:,.0f}")
            click.echo(f"   Median: ${salary['median']:,.0f}")
        
        if stats.get('top_skills'):
            click.echo(f"\n🔧 Top Skills:")
            for skill, count in stats['top_skills'][:5]:
                click.echo(f"   {skill}: {count} jobs")

        click.echo(f"\n💾 Output saved to: {output}")

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--input",
    "-i",
    default=str(settings.default_jobs_output_path),
    help="Input file path"
)
def analyze(input):
    """Analyze saved job data."""
    click.echo(f"📊 Analyzing data from {input}...")
    
    try:
        import pandas as pd
        df = pd.read_csv(input)
        
        click.echo(f"\n📈 Data Overview:")
        click.echo(f"   Total records: {len(df)}")
        click.echo(f"   Columns: {', '.join(df.columns)}")
        
        if 'salary_min' in df.columns:
            salaries = pd.concat([df['salary_min'], df['salary_max']]).dropna()
            click.echo(f"\n💰 Salary Analysis:")
            click.echo(f"   Mean: ${salaries.mean():,.0f}")
            click.echo(f"   Median: ${salaries.median():,.0f}")
            click.echo(f"   Min: ${salaries.min():,.0f}")
            click.echo(f"   Max: ${salaries.max():,.0f}")
        
        if 'location' in df.columns:
            click.echo(f"\n📍 Top Locations:")
            for location, count in df['location'].value_counts().head(5).items():
                click.echo(f"   {location}: {count}")
        
        if 'company' in df.columns:
            click.echo(f"\n🏢 Top Companies:")
            for company, count in df['company'].value_counts().head(5).items():
                click.echo(f"   {company}: {count}")
    
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command("track-experiment")
@click.option(
    "--train-data",
    default=str(settings.training_data_path),
    help="Training dataset path"
)
@click.option(
    "--eval-data",
    default=str(settings.production_data_path),
    help="Evaluation dataset path"
)
@click.option(
    "--experiment-name",
    default=None,
    help="Override MLflow experiment name"
)
@click.option(
    "--run-name",
    default=None,
    help="Custom MLflow run name"
)
@click.option(
    "--tracking-uri",
    default=None,
    help="Override MLflow tracking URI"
)
@click.option(
    "--artifact-root",
    default=None,
    help="Override MLflow artifact root"
)
@click.option(
    "--registered-model-name",
    default=None,
    help="Override the MLflow registered model name"
)
@click.option(
    "--skip-registry",
    is_flag=True,
    help="Do not register the model in the MLflow model registry"
)
def track_experiment(
    train_data,
    eval_data,
    experiment_name,
    run_name,
    tracking_uri,
    artifact_root,
    registered_model_name,
    skip_registry,
):
    """Train and track a role prediction experiment with MLflow."""
    click.echo("🧪 Running MLflow experiment tracking...")
    click.echo(f"   Training data: {train_data}")
    click.echo(f"   Evaluation data: {eval_data}")

    try:
        predictor = RolePredictor()
        result = predictor.run_experiment(
            training_data_path=train_data,
            evaluation_data_path=eval_data,
            tracking_uri=tracking_uri,
            experiment_name=experiment_name,
            artifact_root=artifact_root,
            registered_model_name=registered_model_name,
            run_name=run_name,
            register_model=not skip_registry,
        )

        click.echo("\n✅ Experiment tracked successfully")
        click.echo(f"   Run ID: {result['run_id']}")
        click.echo(f"   Tracking URI: {result['tracking_uri']}")
        click.echo(f"   Accuracy: {result['metrics']['accuracy']:.3f}")
        click.echo(f"   Macro F1: {result['metrics']['f1_macro']:.3f}")

        if result.get("registered_model_name"):
            click.echo(
                "   Registered model: "
                f"{result['registered_model_name']} v{result['registered_model_version']}"
            )
        else:
            click.echo("   Model registry: skipped")

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
